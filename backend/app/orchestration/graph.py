"""
LangGraph orchestration graph builder.

Defines the shared state and builds the state graph workflow:
START -> Planner -> Research -> Coder -> Tester -> Reviewer -> END
"""

from typing import TypedDict, Annotated
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


def create_agent_graph(ollama_client: OllamaClient) -> StateGraph:
    """
    Build and compile the LangGraph workflow.
    """
    # Instantiate agents with MCP tool runners
    planner = PlannerAgent(ollama_client)
    research = ResearchAgent(ollama_client)
    coder = CoderAgent(ollama_client)
    tester = TesterAgent(ollama_client)
    reviewer = ReviewerAgent(ollama_client)

    # Define node functions
    async def planner_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Planner")
        tool_runner = MCPToolRunner("planner")
        output = await planner.execute(state["user_request"], tool_runner=tool_runner)
        invocations = [
            {"agent": r.agent_name, "tool": r.tool_name, "status": r.status,
             "execution_time": r.execution_time, "arguments": r.arguments,
             "result_summary": r.result_summary}
            for r in tool_runner.get_invocations()
        ]
        return {
            "execution_plan": output,
            "current_agent": "planner",
            "tool_invocations": state.get("tool_invocations", []) + invocations,
        }

    async def research_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Research")
        tool_runner = MCPToolRunner("research")
        output = await research.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            tool_runner=tool_runner,
        )
        invocations = [
            {"agent": r.agent_name, "tool": r.tool_name, "status": r.status,
             "execution_time": r.execution_time, "arguments": r.arguments,
             "result_summary": r.result_summary}
            for r in tool_runner.get_invocations()
        ]
        return {
            "research_notes": output,
            "current_agent": "research",
            "tool_invocations": state.get("tool_invocations", []) + invocations,
        }

    async def coder_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Coder")
        tool_runner = MCPToolRunner("coder")
        output = await coder.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            research_notes=state["research_notes"],
            tool_runner=tool_runner,
        )
        invocations = [
            {"agent": r.agent_name, "tool": r.tool_name, "status": r.status,
             "execution_time": r.execution_time, "arguments": r.arguments,
             "result_summary": r.result_summary}
            for r in tool_runner.get_invocations()
        ]
        return {
            "generated_code": output,
            "current_agent": "coder",
            "tool_invocations": state.get("tool_invocations", []) + invocations,
        }

    async def tester_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Tester")
        tool_runner = MCPToolRunner("tester")
        output = await tester.execute(
            generated_code=state["generated_code"],
            execution_plan=state["execution_plan"],
            tool_runner=tool_runner,
        )
        invocations = [
            {"agent": r.agent_name, "tool": r.tool_name, "status": r.status,
             "execution_time": r.execution_time, "arguments": r.arguments,
             "result_summary": r.result_summary}
            for r in tool_runner.get_invocations()
        ]
        return {
            "test_results": output,
            "current_agent": "tester",
            "tool_invocations": state.get("tool_invocations", []) + invocations,
        }

    async def reviewer_node(state: AgentState) -> dict:
        logger.info("LangGraph Node: Reviewer")
        tool_runner = MCPToolRunner("reviewer")
        output = await reviewer.execute(
            user_request=state["user_request"],
            execution_plan=state["execution_plan"],
            generated_code=state["generated_code"],
            test_results=state["test_results"],
            research_notes=state["research_notes"],
            tool_runner=tool_runner,
        )
        invocations = [
            {"agent": r.agent_name, "tool": r.tool_name, "status": r.status,
             "execution_time": r.execution_time, "arguments": r.arguments,
             "result_summary": r.result_summary}
            for r in tool_runner.get_invocations()
        ]
        return {
            "review": output,
            "current_agent": "reviewer",
            "tool_invocations": state.get("tool_invocations", []) + invocations,
        }

    # Initialize State Graph
    builder = StateGraph(AgentState)

    # Add Nodes
    builder.add_node("planner", planner_node)
    builder.add_node("research", research_node)
    builder.add_node("coder", coder_node)
    builder.add_node("tester", tester_node)
    builder.add_node("reviewer", reviewer_node)

    # Add Edges
    builder.add_edge(START, "planner")
    builder.add_edge("planner", "research")
    builder.add_edge("research", "coder")
    builder.add_edge("coder", "tester")
    builder.add_edge("tester", "reviewer")
    builder.add_edge("reviewer", END)

    # Compile Graph
    return builder.compile()
