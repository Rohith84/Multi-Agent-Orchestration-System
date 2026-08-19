"""
Workflow Executor and Execution Manager with Autonomous Self-Repair, File Persistence, and Quality Gates.

Runs the LangGraph orchestration flow step-by-step with automatic code repair loops and state persistence.
"""

from __future__ import annotations

import asyncio
import time
import json
import uuid
from datetime import datetime
from typing import AsyncGenerator, Any
from langchain_core.runnables import RunnableConfig
from sqlalchemy.ext.asyncio import AsyncSession

from app.orchestration.graph import create_agent_graph, AgentState
from app.ai.ollama_client import OllamaClient
from app.repositories.agent_repository import AgentExecutionRepository
from app.repositories.chat_repository import ChatRepository
from app.repositories.tool_repository import ToolExecutionRepository
from app.repositories.workflow_repository import WorkflowRepository
from app.knowledge.vectorstore.planning_memory import PlanningMemoryStore
from app.services.workspace_service import WorkspaceService
from app.models.metrics import AgentMetric, WorkflowMetric
from app.models.workspace import TestReport, QualityReport
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)

AGENT_PROGRESS_MAP = {
    "planner": 20,
    "research": 40,
    "coder": 60,
    "tester": 80,
    "reviewer": 100,
}

AGENT_MODEL_MAP = {
    "planner": "llama3.1:8b",
    "research": "llama3.1:8b",
    "coder": "qwen2.5-coder:7b",
    "tester": "qwen2.5-coder:7b",
    "reviewer": "llama3.1:8b",
}


class WorkflowExecutor:
    """
    Coordinates LangGraph execution, self-repair loops, file persistence, and quality gates.
    """

    _cancellation_events: dict[uuid.UUID, asyncio.Event] = {}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.agent_repo = AgentExecutionRepository(db)
        self.chat_repo = ChatRepository(db)
        self.tool_repo = ToolExecutionRepository(db)
        self.wf_repo = WorkflowRepository(db)
        self.planning_memory_store = PlanningMemoryStore()
        self.ollama = OllamaClient()
        self.settings = get_settings()

    @classmethod
    def request_cancellation(cls, workflow_id: uuid.UUID) -> None:
        """Signal a locally running workflow to stop at its next safe boundary."""
        event = cls._cancellation_events.get(workflow_id)
        if event:
            event.set()

    @staticmethod
    def _next_agent(node_name: str, state: AgentState) -> str:
        if node_name == "planner":
            return "research"
        if node_name == "research":
            return "coder"
        if node_name == "coder":
            return "tester"
        if node_name == "tester":
            return "reviewer" if state.get("test_passed") else "coder"
        return "end"

    async def execute(
        self,
        user_request: str,
        session_id: uuid.UUID,
        require_approval_agents: list[str] | None = None,
        workflow_id: uuid.UUID | None = None,
        resume_agent: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Executes the multi-agent graph with self-repair feedback loops and yields SSE updates.
        """
        require_approval_agents = [agent.lower() for agent in (require_approval_agents or [])]
        workspace = WorkspaceService(self.db, session_id=session_id)

        # 1. Resolve or create Workflow DB record
        if workflow_id:
            wf = await self.wf_repo.get_workflow(workflow_id)
            if not wf:
                yield self._format_sse_event({"event": "workflow_failed", "error": "Workflow not found."})
                return
        else:
            wf = await self.wf_repo.create_workflow(
                session_id=session_id,
                user_request=user_request,
                require_approval_agents=require_approval_agents,
            )
            workflow_id = wf.id

        # Emit immediate workflow_started event so frontend receives IDs right away
        yield self._format_sse_event({
            "event": "workflow_started",
            "workflow_id": str(workflow_id),
            "session_id": str(session_id),
            "message": "Workflow execution started",
        })

        # 2. Save user message if starting fresh
        if not resume_agent:
            await self.chat_repo.save_message(
                session_id=session_id,
                role="user",
                message=user_request,
                model=None,
            )
            await self.db.commit()

        initial_state: AgentState = {
            "session_id": str(session_id),
            "user_request": user_request,
            "execution_plan": "",
            "research_notes": "",
            "generated_code": "",
            "test_results": "",
            "review": "",
            "current_agent": "start",
            "errors": [],
            "tool_invocations": [],
            "repair_attempts": 0,
            "test_passed": False,
            "bug_report": None,
            "quality_gate": "PASS",
        }

        if resume_agent:
            cp = await self.wf_repo.get_latest_checkpoint(workflow_id)
            if cp and cp.shared_state:
                initial_state.update(cp.shared_state)

        start_at = str(initial_state.get("next_agent") or resume_agent or "planner")
        if start_at == "end":
            final_answer = initial_state.get("review", "Workflow completed.")
            await self.wf_repo.update_workflow(workflow_id, status="completed", current_agent="end", progress_percentage=100)
            await self.chat_repo.save_message(session_id=session_id, role="assistant", message=final_answer, model=self.settings.model_reviewer)
            await self.db.commit()
            yield self._format_sse_event({"event": "workflow_complete", "workflow_id": str(workflow_id), "session_id": str(session_id), "response": final_answer, "progress_percentage": 100})
            return

        await self.wf_repo.update_workflow(
            workflow_id,
            status="running",
            current_agent=start_at,
        )
        await self.db.commit()

        config: RunnableConfig = {
            "configurable": {
                "db": self.db,
                "session_id": session_id,
                "workflow_id": workflow_id,
                "user_request": user_request,
                "executor": self,
            }
        }

        graph = create_agent_graph(self.ollama, workspace_service=workspace, start_at=start_at)
        current_state = initial_state
        started_at = time.perf_counter()
        cancellation_event = asyncio.Event()
        self._cancellation_events[workflow_id] = cancellation_event

        try:
            # Run compiled LangGraph node stream
            async for output_state in graph.astream(initial_state, config=config):
                if cancellation_event.is_set():
                    await self._mark_cancelled(workflow_id, session_id, time.perf_counter() - started_at)
                    yield self._format_sse_event({"event": "workflow_cancelled", "workflow_id": str(workflow_id)})
                    return

                node_name, node_output = next(iter(output_state.items()))
                if cancellation_event.is_set():
                    await self._mark_cancelled(workflow_id, session_id, time.perf_counter() - started_at)
                    yield self._format_sse_event({"event": "workflow_cancelled", "workflow_id": str(workflow_id)})
                    return
                current_state.update(node_output)
                pct = AGENT_PROGRESS_MAP.get(node_name, 50)
                execution_time = float(node_output.get("execution_time", 0.0))

                yield self._format_sse_event({
                    "event": "agent_start",
                    "agent": node_name,
                    "progress_percentage": pct,
                    "workflow_id": str(workflow_id),
                    "message": f"Agent {node_name.capitalize()} executing..."
                })

                output_text = (
                    node_output.get("execution_plan")
                    or node_output.get("research_notes")
                    or node_output.get("generated_code")
                    or node_output.get("test_results")
                    or node_output.get("review")
                    or ""
                )

                # Stream repair loop event if coder is re-running due to test failure
                if node_name == "coder" and current_state.get("repair_attempts", 0) > 0:
                    yield self._format_sse_event({
                        "event": "repair_loop_retry",
                        "attempt": current_state.get("repair_attempts"),
                        "message": f"Coder repairing code based on test failure (attempt {current_state.get('repair_attempts')}/3)..."
                    })

                # Stream quality gate event when reviewer completes
                if node_name == "reviewer":
                    yield self._format_sse_event({
                        "event": "quality_gate",
                        "decision": current_state.get("quality_gate", "PASS"),
                        "workflow_id": str(workflow_id),
                    })

                # Save execution log & checkpoint
                await self.agent_repo.save_execution(
                    session_id=session_id,
                    agent_name=node_name,
                    input_content=self._get_agent_input(node_name, current_state),
                    output_content=output_text,
                    execution_time=execution_time,
                    status="success",
                )
                next_agent = self._next_agent(node_name, current_state)
                current_state["next_agent"] = next_agent
                await self.wf_repo.save_checkpoint(
                    workflow_id=workflow_id,
                    agent_name=node_name,
                    shared_state=dict(current_state),
                    tool_history=current_state.get("tool_invocations", []),
                    research_context=current_state.get("research_notes", "")[:1000],
                    chat_context=user_request[:500],
                )
                if node_name == "tester":
                    self.db.add(TestReport(
                        workflow_id=workflow_id,
                        passed=bool(current_state.get("test_passed")),
                        execution_time=execution_time,
                        stdout=str(current_state.get("test_results", "")),
                        stderr=str((current_state.get("bug_report") or {}).get("stack_trace", "")),
                        bug_report=current_state.get("bug_report") or {},
                    ))
                if node_name == "reviewer":
                    self.db.add(QualityReport(
                        workflow_id=workflow_id,
                        quality_gate=str(current_state.get("quality_gate", "PASS")),
                    ))
                await self.wf_repo.update_workflow(
                    workflow_id,
                    status="running",
                    current_agent=node_name,
                    progress_percentage=pct,
                    execution_time=round(time.perf_counter() - started_at, 3),
                )
                await self.db.commit()

                yield self._format_sse_event({
                    "event": "agent_end",
                    "agent": node_name,
                    "status": "success",
                    "output": output_text,
                    "execution_time": execution_time,
                    "progress_percentage": pct,
                })

                if node_name in require_approval_agents:
                    await self.wf_repo.create_approval(workflow_id, node_name)
                    await self.wf_repo.update_workflow(
                        workflow_id,
                        status="paused_approval",
                        current_agent=node_name,
                        progress_percentage=pct,
                        execution_time=round(time.perf_counter() - started_at, 3),
                    )
                    await self.db.commit()
                    yield self._format_sse_event({
                        "event": "workflow_paused_approval",
                        "workflow_id": str(workflow_id),
                        "agent": node_name,
                        "next_agent": next_agent,
                        "message": f"Approval required after {node_name.capitalize()}.",
                    })
                    return

            # Save final response
            final_answer = current_state.get("review", "Workflow completed.")
            await self.wf_repo.update_workflow(
                workflow_id,
                status="completed",
                progress_percentage=100,
                current_agent="end",
                execution_time=round(time.perf_counter() - started_at, 3),
            )
            await self.chat_repo.save_message(session_id=session_id, role="assistant", message=final_answer, model=self.settings.model_reviewer)
            await self.db.commit()
            yield self._format_sse_event({"event": "workflow_complete", "workflow_id": str(workflow_id), "session_id": str(session_id), "response": final_answer, "progress_percentage": 100})
        except asyncio.CancelledError:
            await self._mark_cancelled(workflow_id, session_id, time.perf_counter() - started_at)
            raise
        except Exception as exc:
            logger.exception("Workflow %s failed", workflow_id)
            await self.wf_repo.update_workflow(workflow_id, status="failed", error_message=str(exc), execution_time=round(time.perf_counter() - started_at, 3))
            await self.db.commit()
            yield self._format_sse_event({"event": "workflow_failed", "workflow_id": str(workflow_id), "error": "Workflow execution failed."})
        finally:
            self._cancellation_events.pop(workflow_id, None)

    async def _mark_cancelled(self, workflow_id: uuid.UUID, session_id: uuid.UUID, elapsed: float) -> None:
        await self.wf_repo.update_workflow(workflow_id, status="cancelled", error_message="Workflow cancelled by user", execution_time=round(elapsed, 3))
        await self.db.commit()

    def _format_sse_event(self, data: dict) -> str:
        """Helper to format dictionary to SSE data line."""
        return f"data: {json.dumps(data)}\n\n"

    def _get_agent_input(self, agent: str, state: AgentState) -> str:
        """Determines the input string passed to agent."""
        if agent == "planner":
            return state["user_request"]
        elif agent == "research":
            return f"Plan:\n{state.get('execution_plan', '')}"
        elif agent == "coder":
            return f"Plan:\n{state.get('execution_plan', '')}\nResearch:\n{state.get('research_notes', '')}"
        elif agent == "tester":
            return f"Code:\n{state.get('generated_code', '')}"
        elif agent == "reviewer":
            return f"Code:\n{state.get('generated_code', '')}\nTests:\n{state.get('test_results', '')}"
        return ""
