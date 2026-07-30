"""
Workflow Executor and Execution Manager.

Runs the LangGraph orchestration flow step-by-step.
Handles timing, structured logging, PostgreSQL persistence, and retry logic.
Supports Server-Sent Events (SSE) streaming.
"""

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
from app.core.logging import get_logger
from app.core.config import get_settings

logger = get_logger(__name__)


class WorkflowExecutor:
    """
    Coordinates LangGraph execution, database persistence, and retries.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.agent_repo = AgentExecutionRepository(db)
        self.chat_repo = ChatRepository(db)
        self.ollama = OllamaClient()
        self.settings = get_settings()

    async def execute(
        self,
        user_request: str,
        session_id: uuid.UUID,
    ) -> AsyncGenerator[str, None]:
        """
        Executes the multi-agent graph and yields SSE stream updates.
        """
        # 1. Save initial user message in chat history
        await self.chat_repo.save_message(
            session_id=session_id,
            role="user",
            message=user_request,
            model=None,
        )
        await self.db.commit()

        # Build initial state
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
        }

        # Setup LangGraph config to pass repositories and metadata
        config: RunnableConfig = {
            "configurable": {
                "db": self.db,
                "session_id": session_id,
                "user_request": user_request,
                "executor": self,
            }
        }

        # Build compiled graph
        graph = create_agent_graph(self.ollama)

        # Run step-by-step
        current_state = initial_state
        agent_sequence = ["planner", "research", "coder", "tester", "reviewer"]

        for agent in agent_sequence:
            # Yield start event for the agent
            yield self._format_sse_event({
                "event": "agent_start",
                "agent": agent,
                "message": f"Agent {agent.capitalize()} started execution..."
            })

            start_time = time.time()
            success = False
            output = ""
            retried = False

            # Run with retry support
            for attempt in range(2):
                try:
                    # Invoke node manually or via graph update
                    if agent == "planner":
                        res = await graph.nodes["planner"](current_state, config)
                        current_state["execution_plan"] = res["execution_plan"]
                        output = res["execution_plan"]
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

            # Save execution to DB
            input_data = self._get_agent_input(agent, current_state)
            await self.agent_repo.save_execution(
                session_id=session_id,
                agent_name=agent,
                input_content=input_data,
                output_content=output,
                execution_time=duration,
                status=status,
            )
            await self.db.commit()

            # Yield end event
            yield self._format_sse_event({
                "event": "agent_end",
                "agent": agent,
                "status": status,
                "output": output,
                "execution_time": round(duration, 2),
                "retried": retried,
            })

            if not success:
                # Abort workflow on failure
                yield self._format_sse_event({
                    "event": "workflow_failed",
                    "error": f"Workflow aborted due to failure in agent '{agent}'"
                })
                return

        # 2. Save final response to ChatHistory
        final_answer = current_state["review"]
        await self.chat_repo.save_message(
            session_id=session_id,
            role="assistant",
            message=final_answer,
            model=self.settings.model_reviewer,
        )
        await self.db.commit()

        # Yield workflow complete event
        yield self._format_sse_event({
            "event": "workflow_complete",
            "session_id": str(session_id),
            "response": final_answer,
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
