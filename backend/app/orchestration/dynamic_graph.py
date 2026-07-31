"""
Dynamic LangGraph Compiler.

Parses arbitrary graph JSON topologies (nodes, edges, custom agents, conditions) and dynamically constructs executable StateGraph workflows.
"""

from __future__ import annotations

from typing import TypedDict, Any
from langgraph.graph import StateGraph, START, END

from app.ai.ollama_client import OllamaClient
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.coder import CoderAgent
from app.agents.tester import TesterAgent
from app.agents.reviewer import ReviewerAgent
from app.mcp.clients.tool_runner import MCPToolRunner
from app.core.logging import get_logger

logger = get_logger(__name__)


class DynamicAgentState(TypedDict):
    """
    Shared dynamic state passed through custom LangGraph workflows.
    """

    session_id: str
    user_request: str
    current_node: str
    node_outputs: dict[str, str]
    execution_history: list[str]


class DynamicGraphCompiler:
    """
    Compiles custom visual workflow JSON into executable LangGraph StateGraphs.
    """

    def __init__(self, ollama_client: OllamaClient | None = None) -> None:
        self.client = ollama_client or OllamaClient()

    def compile(self, graph_json: dict[str, Any]) -> Any:
        """
        Build and compile a StateGraph dynamically from nodes and edges JSON.
        """
        nodes_list = graph_json.get("nodes", [])
        edges_list = graph_json.get("edges", [])

        logger.info("Compiling Dynamic LangGraph with %d nodes and %d edges", len(nodes_list), len(edges_list))

        builder = StateGraph(DynamicAgentState)

        # 1. Add Nodes
        for n in nodes_list:
            node_id = n.get("id")
            node_type = n.get("type", "planner").lower()

            node_fn = self._create_node_handler(node_id, node_type, n.get("config", {}))
            builder.add_node(node_id, node_fn)

        # 2. Add Edges
        if nodes_list:
            # Connect START to first node
            first_node_id = nodes_list[0]["id"]
            builder.add_edge(START, first_node_id)

            # Connect consecutive nodes according to edges or linear sequence
            if edges_list:
                for edge in edges_list:
                    src = edge.get("source")
                    dst = edge.get("target")
                    if src and dst:
                        builder.add_edge(src, dst)
            else:
                for i in range(len(nodes_list) - 1):
                    builder.add_edge(nodes_list[i]["id"], nodes_list[i + 1]["id"])

            # Connect last node to END
            last_node_id = nodes_list[-1]["id"]
            builder.add_edge(last_node_id, END)

        return builder.compile()

    def _create_node_handler(self, node_id: str, node_type: str, config: dict[str, Any]):
        """Create async node handler closure for given node type."""

        async def _handler(state: DynamicAgentState) -> dict:
            logger.info("Executing Dynamic Graph Node: %s (type=%s)", node_id, node_type)
            outputs = dict(state.get("node_outputs", {}))
            history = list(state.get("execution_history", []))
            history.append(node_id)

            req = state.get("user_request", "")

            if node_type == "planner":
                agent = PlannerAgent(self.client)
                res = await agent.execute(req)
            elif node_type == "research":
                agent = ResearchAgent(self.client)
                res = await agent.execute(req, execution_plan=outputs.get("planner", ""))
            elif node_type == "coder":
                agent = CoderAgent(self.client)
                res = await agent.execute(req, execution_plan=outputs.get("planner", ""), research_notes=outputs.get("research", ""))
            elif node_type == "tester":
                agent = TesterAgent(self.client)
                res_dict = await agent.execute(generated_code=outputs.get("coder", ""), execution_plan=outputs.get("planner", ""))
                res = res_dict["output"]
            elif node_type == "reviewer":
                agent = ReviewerAgent(self.client)
                res_dict = await agent.execute(req, outputs.get("planner", ""), outputs.get("coder", ""), outputs.get("tester", ""))
                res = res_dict["output"]
            else:
                # Custom agent or fallback node
                system_prompt = config.get("system_prompt", f"You are node {node_id}.")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": req},
                ]
                res = await self.client.chat(messages)

            outputs[node_id] = res
            return {
                "current_node": node_id,
                "node_outputs": outputs,
                "execution_history": history,
            }

        return _handler
