"""
Workflow Executor and Execution Manager with Checkpointing and Human-in-the-Loop (HITL) Approvals.

Runs the LangGraph orchestration flow step-by-step.
Handles timing, state checkpointing, approval gates, vector memory indexing, PostgreSQL persistence, and SSE streaming.
"""

from __future__ import annotations

import time
import json
import uuid
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


class WorkflowExecutor:
    """
    Coordinates LangGraph execution, database persistence, state checkpointing, and HITL approvals.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.agent_repo = AgentExecutionRepository(db)
        self.chat_repo = ChatRepository(db)
        self.tool_repo = ToolExecutionRepository(db)
        self.wf_repo = WorkflowRepository(db)
        self.planning_memory_store = PlanningMemoryStore()
        self.ollama = OllamaClient()
        self.settings = get_settings()

    async def execute(
        self,
        user_request: str,
        session_id: uuid.UUID,
        require_approval_agents: list[str] | None = None,
        workflow_id: uuid.UUID | None = None,
        resume_agent: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Executes the multi-agent graph with checkpointing and approval checks, yielding SSE updates.
        """
        require_approval_agents = require_approval_agents or []

        # 1. Resolve or create Workflow DB record
        if workflow_id:
            wf = await self.wf_repo.get_workflow(workflow_id)
        else:
            wf = await self.wf_repo.create_workflow(
                session_id=session_id,
                user_request=user_request,
                require_approval_agents=require_approval_agents,
            )
            workflow_id = wf.id

        # 2. Save user message if starting fresh
        if not resume_agent:
            await self.chat_repo.save_message(
                session_id=session_id,
                role="user",
                message=user_request,
                model=None,
            )
            await self.db.commit()

        # 3. Load state from latest checkpoint if resuming
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
        }

        if resume_agent:
            cp = await self.wf_repo.get_latest_checkpoint(workflow_id)
            if cp and cp.shared_state:
                initial_state.update(cp.shared_state)

        await self.wf_repo.update_workflow(
            workflow_id,
            status="running",
            current_agent=resume_agent or "planner",
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

        graph = create_agent_graph(self.ollama)
        current_state = initial_state
        agent_sequence = ["planner", "research", "coder", "tester", "reviewer"]

        # Skip already completed agents if resuming
        start_idx = 0
        if resume_agent and resume_agent in agent_sequence:
            start_idx = agent_sequence.index(resume_agent)

        for i in range(start_idx, len(agent_sequence)):
            agent = agent_sequence[i]

            # --- Check Approval Gate ---
            if agent in require_approval_agents:
                # Check if approval already granted
                pending_app = await self.wf_repo.get_pending_approval(workflow_id)
                if not pending_app:
                    # Create pending approval request and pause
                    app_rec = await self.wf_repo.create_approval(workflow_id, agent)
                    await self.wf_repo.update_workflow(
                        workflow_id,
                        status="paused_approval",
                        current_agent=agent,
                    )
                    await self.db.commit()

                    yield self._format_sse_event({
                        "event": "workflow_paused_approval",
                        "workflow_id": str(workflow_id),
                        "agent": agent,
                        "approval_id": str(app_rec.id),
                        "message": f"Agent {agent.capitalize()} requires human approval to proceed.",
                    })
                    return
                elif pending_app.status == "pending":
                    yield self._format_sse_event({
                        "event": "workflow_paused_approval",
                        "workflow_id": str(workflow_id),
                        "agent": agent,
                        "approval_id": str(pending_app.id),
                        "message": f"Agent {agent.capitalize()} is waiting for human approval.",
                    })
                    return
                elif pending_app.status == "rejected":
                    yield self._format_sse_event({
                        "event": "workflow_failed",
                        "workflow_id": str(workflow_id),
                        "error": f"Workflow rejected at agent '{agent}' by user.",
                    })
                    return

            # Yield start & progress event
            pct = AGENT_PROGRESS_MAP.get(agent, 0)
            await self.wf_repo.update_workflow(
                workflow_id,
                current_agent=agent,
                progress_percentage=pct,
            )
            await self.db.commit()

            yield self._format_sse_event({
                "event": "agent_start",
                "agent": agent,
                "progress_percentage": pct,
                "workflow_id": str(workflow_id),
                "message": f"Agent {agent.capitalize()} started execution..."
            })

            start_time = time.time()
            success = False
            output = ""
            retried = False

            # Run agent with retry support
            for attempt in range(2):
                try:
                    if agent == "planner":
                        res = await graph.nodes["planner"](current_state, config)
                        current_state["execution_plan"] = res["execution_plan"]
                        output = res["execution_plan"]

                        # Index plan into Planning Memory (DB + Chroma)
                        try:
                            mem_rec = await self.wf_repo.save_planning_memory(
                                goal=user_request,
                                plan=output,
                            )
                            await self.planning_memory_store.add_plan(
                                memory_id=mem_rec.id,
                                goal=user_request,
                                plan=output,
                            )
                        except Exception as e:
                            logger.warning("Failed to save planning memory: %s", e)

                    elif agent == "research":
                        res = await graph.nodes["research"](current_state, config)
                        current_state["research_notes"] = res["research_notes"]
                        output = res["research_notes"]
                    elif agent == "coder":
                        res = await graph.nodes["coder"](current_state, config)
                        current_state["generated_code"] = res["generated_code"]
                        output = res["generated_code"]
                    elif agent == "tester":
                        res = await graph.nodes["tester"](current_state, config)
                        current_state["test_results"] = res["test_results"]
                        output = res["test_results"]
                    elif agent == "reviewer":
                        res = await graph.nodes["reviewer"](current_state, config)
                        current_state["review"] = res["review"]
                        output = res["review"]

                    success = True
                    break
                except Exception as e:
                    logger.error(
                        "Error running agent %s (attempt %d/2): %s",
                        agent,
                        attempt + 1,
                        str(e),
                    )
                    if attempt == 0:
                        retried = True
                        yield self._format_sse_event({
                            "event": "agent_retry",
                            "agent": agent,
                            "error": str(e),
                            "message": f"Agent {agent.capitalize()} failed. Retrying..."
                        })
                        time.sleep(1.0)
                    else:
                        current_state["errors"].append(f"{agent}: {str(e)}")
                        output = f"Execution failed: {str(e)}"

            duration = time.time() - start_time
            status = "success" if success else "failed"

            # Save Agent Execution log
            input_data = self._get_agent_input(agent, current_state)
            await self.agent_repo.save_execution(
                session_id=session_id,
                agent_name=agent,
                input_content=input_data,
                output_content=output,
                execution_time=duration,
                status=status,
            )

            # Checkpoint workflow state
            try:
                cp = await self.wf_repo.save_checkpoint(
                    workflow_id=workflow_id,
                    agent_name=agent,
                    shared_state=dict(current_state),
                    tool_history=current_state.get("tool_invocations", []),
                    research_context=current_state.get("research_notes", "")[:1000],
                    chat_context=user_request[:500],
                )
                yield self._format_sse_event({
                    "event": "checkpoint_created",
                    "checkpoint_id": str(cp.id),
                    "agent": agent,
                })
            except Exception as e:
                logger.warning("Failed to save workflow checkpoint: %s", e)

            await self.db.commit()

            # Yield end event
            yield self._format_sse_event({
                "event": "agent_end",
                "agent": agent,
                "status": status,
                "output": output,
                "execution_time": round(duration, 2),
                "retried": retried,
                "progress_percentage": pct,
            })

            # Emit tool execution events for MCP tools
            agent_tool_invocations = [
                inv for inv in current_state.get("tool_invocations", [])
                if inv.get("agent") == agent
            ]
            for inv in agent_tool_invocations:
                yield self._format_sse_event({
                    "event": "tool_execution",
                    "agent": inv["agent"],
                    "tool_name": inv["tool"],
                    "status": inv["status"],
                    "execution_time": inv["execution_time"],
                })
                try:
                    await self.tool_repo.save_execution(
                        agent_name=inv["agent"],
                        tool_name=inv["tool"],
                        arguments=inv.get("arguments", {}),
                        status=inv["status"],
                        execution_time=inv["execution_time"],
                        result_summary=inv.get("result_summary", "")[:500],
                    )
                    await self.db.commit()
                except Exception as e:
                    logger.warning("Failed to persist tool execution: %s", e)

            if not success:
                await self.wf_repo.update_workflow(
                    workflow_id,
                    status="failed",
                    error_message=f"Failed at agent '{agent}'",
                )
                await self.db.commit()
                yield self._format_sse_event({
                    "event": "workflow_failed",
                    "workflow_id": str(workflow_id),
                    "error": f"Workflow aborted due to failure in agent '{agent}'"
                })
                return

        # Mark workflow complete & save final chat answer
        final_answer = current_state["review"]
        await self.wf_repo.update_workflow(
            workflow_id,
            status="completed",
            progress_percentage=100,
            current_agent="end",
        )
        await self.chat_repo.save_message(
            session_id=session_id,
            role="assistant",
            message=final_answer,
            model=self.settings.model_reviewer,
        )
        await self.db.commit()

        yield self._format_sse_event({
            "event": "workflow_complete",
            "workflow_id": str(workflow_id),
            "session_id": str(session_id),
            "response": final_answer,
            "progress_percentage": 100,
        })

    def _format_sse_event(self, data: dict) -> str:
        """Helper to format dictionary to SSE data line."""
        return f"data: {json.dumps(data)}\n\n"

    def _get_agent_input(self, agent: str, state: AgentState) -> str:
        """Determines the exact input string that was passed to the agent."""
        if agent == "planner":
            return state["user_request"]
        elif agent == "research":
            return f"Plan:\n{state['execution_plan']}"
        elif agent == "coder":
            return f"Plan:\n{state['execution_plan']}\nResearch:\n{state['research_notes']}"
        elif agent == "tester":
            return f"Code:\n{state['generated_code']}"
        elif agent == "reviewer":
            return f"Code:\n{state['generated_code']}\nTests:\n{state['test_results']}"
        return ""
