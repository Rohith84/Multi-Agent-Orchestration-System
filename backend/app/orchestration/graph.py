"""
LangGraph orchestration graph builder with Autonomous Self-Repair Loop.

Defines the shared state and builds the state graph workflow:
START -> Planner -> Research -> Coder -> Tester -> (Conditional Repair Loop) -> Reviewer -> END
"""

from typing import TypedDict, Any
import time
from langgraph.graph import StateGraph, START, END

from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.coder import CoderAgent
from app.agents.tester import TesterAgent
from app.agents.reviewer import ReviewerAgent
from app.ai.ollama_client import OllamaClient
from app.mcp.clients.tool_runner import MCPToolRunner
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    """
    Shared state passed through the LangGraph workflow.
    """
    session_id: str
    user_request: str
    execution_plan: str
    research_notes: str
    generated_code: str
    test_results: str
    review: str
    current_agent: str
    errors: list[str]
    tool_invocations: list[dict]
    repair_attempts: int
    test_passed: bool
    bug_report: dict[str, Any] | None
    quality_gate: str
    next_agent: str
    execution_time: float


def create_agent_graph(
    ollama_client: OllamaClient,
    workspace_service: Any | None = None,
    start_at: str = "planner",
) -> StateGraph:
    """
    Build and compile the LangGraph workflow with autonomous self-repair logic.
    """
    planner = PlannerAgent(ollama_client)
    research = ResearchAgent(ollama_client)
    coder = CoderAgent(ollama_client)
    tester = TesterAgent(ollama_client)
    reviewer = ReviewerAgent(ollama_client)

    async def planner_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Planner")
        started = time.perf_counter()
        tool_runner = MCPToolRunner("planner")
        output = await planner.execute(state["user_request"], tool_runner=tool_runner)
        return {
            "execution_plan": output,
            "current_agent": "planner",
            "repair_attempts": 0,
            "test_passed": False,
            "execution_time": round(time.perf_counter() - started, 3),
        }

    async def research_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Research")
        started = time.perf_counter()
        tool_runner = MCPToolRunner("research")
        output = await research.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            tool_runner=tool_runner,
        )
        return {
            "research_notes": output,
            "current_agent": "research",
            "execution_time": round(time.perf_counter() - started, 3),
        }

    async def coder_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Coder (attempt %d)", state.get("repair_attempts", 0) + 1)
        started = time.perf_counter()
        tool_runner = MCPToolRunner("coder")
        output = await coder.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            research_notes=state["research_notes"],
            bug_report=state.get("bug_report"),
            workspace_service=workspace_service,
            tool_runner=tool_runner,
        )
        return {
            "generated_code": output,
            "current_agent": "coder",
            "execution_time": round(time.perf_counter() - started, 3),
        }

    async def tester_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Tester")
        started = time.perf_counter()
        tool_runner = MCPToolRunner("tester")
        res = await tester.execute(
            generated_code=state["generated_code"],
            execution_plan=state["execution_plan"],
            workspace_service=workspace_service,
            tool_runner=tool_runner,
        )
        attempts = state.get("repair_attempts", 0) + (0 if res["passed"] else 1)
        return {
            "test_results": res["output"],
            "test_passed": res["passed"],
            "bug_report": res.get("bug_report"),
            "repair_attempts": attempts,
            "current_agent": "tester",
            "execution_time": round(time.perf_counter() - started, 3),
        }

    async def reviewer_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Reviewer")
        started = time.perf_counter()
        tool_runner = MCPToolRunner("reviewer")
        res = await reviewer.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            generated_code=state["generated_code"],
            test_results=state["test_results"],
            research_notes=state["research_notes"],
            tool_runner=tool_runner,
        )
        return {
            "review": res["output"],
            "quality_gate": res["quality_gate"],
            "current_agent": "reviewer",
            "execution_time": round(time.perf_counter() - started, 3),
        }

    def should_repair_code(state: AgentState) -> str:
        """Conditional routing: loop back to coder if test failed and attempts < 3."""
        if not state.get("test_passed", True) and state.get("repair_attempts", 0) < 3:
            logger.info("Routing back to Coder for automatic code repair (attempt %d)", state.get("repair_attempts"))
            return "coder"
        return "reviewer"

    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("research", research_node)
    builder.add_node("coder", coder_node)
    builder.add_node("tester", tester_node)
    builder.add_node("reviewer", reviewer_node)

    valid_starts = {"planner", "research", "coder", "tester", "reviewer"}
    if start_at not in valid_starts:
        raise ValueError(f"Unknown workflow resume agent: {start_at}")

    builder.add_edge(START, start_at)
    if start_at == "planner":
        builder.add_edge("planner", "research")
    if start_at in {"planner", "research"}:
        builder.add_edge("research", "coder")
    if start_at != "reviewer":
        builder.add_edge("coder", "tester")
    if start_at in {"planner", "research", "coder", "tester"}:
        builder.add_conditional_edges("tester", should_repair_code, {"coder": "coder", "reviewer": "reviewer"})
    builder.add_edge("reviewer", END)

    return builder.compile()
