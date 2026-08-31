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
        req_agents = state.get("required_agents", [])
        if node_name == "planner":
            if "research" in req_agents:
                return "research"
            if "coder" in req_agents:
                return "coder"
            if "reviewer" in req_agents:
                return "reviewer"
            return "end"
        if node_name == "research":
            if "coder" in req_agents:
                return "coder"
            if "reviewer" in req_agents:
                return "reviewer"
            return "end"
        if node_name == "coder":
            if "tester" in req_agents:
                return "tester"
            if "reviewer" in req_agents:
                return "reviewer"
            return "end"
        if node_name == "tester":
            return "validator"
        if node_name == "validator":
            if not state.get("test_passed", False) and state.get("repair_attempts", 0) < 3:
                return "coder"
            if "reviewer" in req_agents:
                return "reviewer"
            return "end"
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
            "required_agents": [],
            "research_notes": "",
            "generated_code": "",
            "test_results": "",
            "tester_analysis": "",
            "validation_results": {},
            "review": "",
            "current_agent": "start",
            "errors": [],
            "tool_invocations": [],
            "repair_attempts": 0,
            "test_passed": False,
            "bug_report": None,
            "quality_gate": "PENDING",
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

                # Validator (Quality Gate) is an internal infrastructure node, not an LLM agent card
                if node_name == "validator":
                    if not current_state.get("test_passed", False):
                        yield self._format_sse_event({
                            "event": "repair_loop_retry",
                            "attempt": current_state.get("repair_attempts", 1),
                            "message": f"Quality Gate failed — Coder repairing code (attempt {current_state.get('repair_attempts', 1)}/3)..."
                        })
                    else:
                        yield self._format_sse_event({
                            "event": "quality_gate",
                            "decision": current_state.get("quality_gate", "PENDING"),
                            "workflow_id": str(workflow_id),
                            "message": f"Quality Gate: {current_state.get('quality_gate', 'PENDING')}",
                        })
                    continue

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

                # Determine accurate node execution status
                node_status = "success"
                if node_name == "tester":
                    # Tester generates tests, doesn't determine pass/fail
                    node_status = "success"
                elif node_name == "reviewer" and current_state.get("quality_gate") == "FAIL":
                    node_status = "failed"

                # Save execution log & checkpoint
                await self.agent_repo.save_execution(
                    session_id=session_id,
                    agent_name=node_name,
                    input_content=self._get_agent_input(node_name, current_state),
                    output_content=output_text,
                    execution_time=execution_time,
                    status=node_status,
                )
                
                # Save AgentMetric
                from app.models.metrics import AgentMetric
                from app.orchestration.router import get_model_for_agent
                from datetime import timedelta
                
                model_used = get_model_for_agent(node_name)
                
                agent_score = 9.0
                eval_breakdown = {}
                if node_name == "reviewer":
                    raw_score = current_state.get("overall_score", 90.0)
                    agent_score = raw_score / 10.0 if raw_score > 10.0 else raw_score
                    eval_breakdown = {
                        "accuracy": agent_score,
                        "completeness": agent_score,
                        "correctness": agent_score,
                        "safety": 10.0
                    }
                elif node_name == "tester":
                    # Tester generates tests — score based on test generation, not execution
                    agent_score = 8.0  # Default good score for test generation
                
                self.db.add(AgentMetric(
                    workflow_id=workflow_id,
                    agent_name=node_name,
                    model=model_used,
                    start_time=datetime.utcnow() - timedelta(seconds=execution_time),
                    end_time=datetime.utcnow(),
                    duration=execution_time,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    status=node_status,
                    retry_count=current_state.get("repair_attempts", 0) if node_name in ("coder", "tester") else 0,
                    tool_calls=len(current_state.get("tool_invocations", [])),
                    knowledge_chunks=0,
                    score=agent_score,
                    eval_breakdown=eval_breakdown,
                ))

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
                        overall_score=float(current_state.get("overall_score", 90.0) / 10.0),
                        lint_findings=current_state.get("lint_findings", []),
                        security_findings=current_state.get("security_findings", []),
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
                    "status": node_status,
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

            # Determine final workflow status
            final_answer = current_state.get("review", "Workflow completed.")
            final_status = "failed" if (current_state.get("quality_gate") == "FAIL" or not current_state.get("test_passed", False)) else "completed"

            await self.wf_repo.update_workflow(
                workflow_id,
                status=final_status,
                progress_percentage=100,
                current_agent="end",
                execution_time=round(time.perf_counter() - started_at, 3),
            )
            await self.chat_repo.save_message(session_id=session_id, role="assistant", message=final_answer, model=self.settings.model_reviewer)
            
            # Save final WorkflowMetric
            from app.models.metrics import WorkflowMetric
            raw_score = current_state.get("overall_score", 90.0)
            final_score = raw_score / 10.0 if raw_score > 10.0 else raw_score
            self.db.add(WorkflowMetric(
                workflow_id=workflow_id,
                total_duration=round(time.perf_counter() - started_at, 3),
                total_tokens=0,
                approval_wait_time=0.0,
                tool_execution_time=0.0,
                rag_time=0.0,
                overall_score=float(final_score),
            ))
            
            await self.db.commit()
            yield self._format_sse_event({
                "event": "workflow_complete",
                "workflow_id": str(workflow_id),
                "session_id": str(session_id),
                "response": final_answer,
                "progress_percentage": 100,
                "status": final_status,
                "quality_gate": current_state.get("quality_gate", "PASS"),
            })
        except asyncio.CancelledError:
            await self._mark_cancelled(workflow_id, session_id, time.perf_counter() - started_at)
            raise
        except Exception as exc:
            logger.exception("Workflow %s failed", workflow_id)
            await self.wf_repo.update_workflow(workflow_id, status="failed", error_message=str(exc), execution_time=round(time.perf_counter() - started_at, 3))
            
            # Save failed WorkflowMetric
            from app.models.metrics import WorkflowMetric
            self.db.add(WorkflowMetric(
                workflow_id=workflow_id,
                total_duration=round(time.perf_counter() - started_at, 3),
                total_tokens=0,
                approval_wait_time=0.0,
                tool_execution_time=0.0,
                rag_time=0.0,
                overall_score=0.0,
            ))
            
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
