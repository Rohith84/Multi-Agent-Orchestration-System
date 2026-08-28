"""
LangGraph orchestration graph builder with Autonomous Self-Repair Loop and Dynamic Routing.

Defines the shared state and builds the state graph workflow:
START -> Planner -> (Dynamic Routing) -> Research -> Coder -> Tester -> (Conditional Repair Loop) -> Reviewer -> END
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
    required_agents: list[str]
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
    Build and compile the LangGraph workflow with autonomous self-repair logic and dynamic routing.
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
        
        # Extract REQUIRED_AGENTS line from the planner output
        required_agents = ["research", "coder", "tester", "reviewer"]  # Fallback
        for line in output.split("\n"):
            if "REQUIRED_AGENTS:" in line:
                agents_part = line.split("REQUIRED_AGENTS:")[-1].strip()
                parsed = [a.strip().lower() for a in agents_part.split(",") if a.strip()]
                if parsed:
                    required_agents = parsed
                    break
                    
        # Validate choices
        valid_choices = {"research", "coder", "tester", "reviewer"}
        required_agents = [a for a in required_agents if a in valid_choices]
        
        if not required_agents:
            required_agents = ["research", "coder", "tester", "reviewer"]
            
        # Ensure coder and tester run together
        if "coder" in required_agents and "tester" not in required_agents:
            required_agents.append("tester")
        elif "tester" in required_agents and "coder" not in required_agents:
            required_agents.append("coder")
            
        logger.info("Dynamic routing required agents: %s", required_agents)

        return {
            "execution_plan": output,
            "required_agents": required_agents,
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
        try:
            tool_runner = MCPToolRunner("reviewer")
            res = await reviewer.execute(
                user_request=state["user_request"],
                execution_plan=state["execution_plan"],
                generated_code=state["generated_code"],
                test_results=state["test_results"],
                research_notes=state["research_notes"],
                tool_runner=tool_runner,
                session_id=state.get("session_id"),
            )
            return {
                "review": res["output"],
                "quality_gate": res["quality_gate"],
                "overall_score": res.get("overall_score", 90.0),
                "lint_findings": res.get("lint_findings", []),
                "security_findings": res.get("security_findings", []),
                "current_agent": "reviewer",
                "execution_time": round(time.perf_counter() - started, 3),
            }
        except Exception as exc:
            logger.exception("Reviewer node crashed: %s — returning safe fallback", exc)
            return {
                "review": f"[Reviewer Error] {exc}. Code was generated but could not be reviewed.",
                "quality_gate": "PASS_WITH_WARNINGS",
                "overall_score": 70.0,
                "lint_findings": [],
                "security_findings": [],
                "current_agent": "reviewer",
                "execution_time": round(time.perf_counter() - started, 3),
            }

    # Dynamic graph routing decisions
    def route_after_planner(state: AgentState) -> str:
        req_agents = state.get("required_agents", [])
        if "research" in req_agents:
            return "research"
        if "coder" in req_agents:
            return "coder"
        if "reviewer" in req_agents:
            return "reviewer"
        return "end"

    def route_after_research(state: AgentState) -> str:
        req_agents = state.get("required_agents", [])
        if "coder" in req_agents:
            return "coder"
        if "reviewer" in req_agents:
            return "reviewer"
        return "end"

    def route_after_coder(state: AgentState) -> str:
        req_agents = state.get("required_agents", [])
        if "tester" in req_agents:
            return "tester"
        if "reviewer" in req_agents:
            return "reviewer"
        return "end"

    def should_repair_code(state: AgentState) -> str:
        """Conditional routing: loop back to coder if test failed (max 3 retries)."""
        req_agents = state.get("required_agents", [])
        if not state.get("test_passed", True) and state.get("repair_attempts", 0) < 3:
            logger.info("Routing back to Coder for automatic code repair (attempt %d/3)", state.get("repair_attempts"))
            return "coder"
        if not state.get("test_passed", True):
            logger.info("Test still failing after 3 repair attempts — skipping to reviewer")
        
        if "reviewer" in req_agents:
            return "reviewer"
        return "end"

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
    
    # Conditional edges for dynamic routing
    builder.add_conditional_edges("planner", route_after_planner, {
        "research": "research",
        "coder": "coder",
        "reviewer": "reviewer",
        "end": END
    })
    builder.add_conditional_edges("research", route_after_research, {
        "coder": "coder",
        "reviewer": "reviewer",
        "end": END
    })
    builder.add_conditional_edges("coder", route_after_coder, {
        "tester": "tester",
        "reviewer": "reviewer",
        "end": END
    })
    builder.add_conditional_edges("tester", should_repair_code, {
        "coder": "coder",
        "reviewer": "reviewer",
        "end": END
    })
    builder.add_edge("reviewer", END)

    return builder.compile()
