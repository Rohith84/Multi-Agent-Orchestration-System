"""
LangGraph orchestration graph builder with Autonomous Self-Repair Loop.

Defines the shared state and builds the state graph workflow:
START -> Planner -> Research -> Coder -> Tester -> (Conditional Repair Loop) -> Reviewer -> END
"""

from typing import TypedDict, Annotated, Any
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


def create_agent_graph(ollama_client: OllamaClient) -> StateGraph:
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
        tool_runner = MCPToolRunner("planner")
        output = await planner.execute(state["user_request"], tool_runner=tool_runner)
        return {
            "execution_plan": output,
            "current_agent": "planner",
            "repair_attempts": 0,
            "test_passed": False,
        }

    async def research_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Research")
        tool_runner = MCPToolRunner("research")
        output = await research.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            tool_runner=tool_runner,
        )
        return {
            "research_notes": output,
            "current_agent": "research",
        }

    async def coder_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Coder (attempt %d)", state.get("repair_attempts", 0) + 1)
        tool_runner = MCPToolRunner("coder")
        output = await coder.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            research_notes=state["research_notes"],
            bug_report=state.get("bug_report"),
            tool_runner=tool_runner,
        )
        return {
            "generated_code": output,
            "current_agent": "coder",
        }

    async def tester_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Tester")
        tool_runner = MCPToolRunner("tester")
        res = await tester.execute(
            generated_code=state["generated_code"],
            execution_plan=state["execution_plan"],
            tool_runner=tool_runner,
        )
        attempts = state.get("repair_attempts", 0) + (0 if res["passed"] else 1)
        return {
            "test_results": res["output"],
            "test_passed": res["passed"],
            "bug_report": res.get("bug_report"),
            "repair_attempts": attempts,
            "current_agent": "tester",
        }

    async def reviewer_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Reviewer")
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

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "research")
    builder.add_edge("research", "coder")
    builder.add_edge("coder", "tester")
    builder.add_conditional_edges("tester", should_repair_code, {"coder": "coder", "reviewer": "reviewer"})
    builder.add_edge("reviewer", END)

    return builder.compile()
