"""
Dynamic LangGraph Compiler.

Parses arbitrary graph JSON topologies (nodes, edges, custom agents, conditions) and dynamically constructs executable StateGraph workflows.
Integrates deterministic contract boundaries (PlanContract, CodeContract, Quality Gate, Evidence-Bound Reviewer) into actual graph execution paths.
"""

from __future__ import annotations

from typing import TypedDict, Any, TYPE_CHECKING
from pathlib import Path
from langgraph.graph import StateGraph, START, END

from app.ai.ollama_client import OllamaClient
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.coder import CoderAgent
from app.agents.tester import TesterAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.validator import DeterministicValidator
from app.orchestration.code_contract import CodeContractValidator
from app.orchestration.graph_validator import GraphContractValidator, GraphContractValidationError
from app.services.workspace_service import WorkspaceService
from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class DynamicAgentState(TypedDict, total=False):
    """
    Shared dynamic state passed through custom LangGraph workflows.
    """

    session_id: str
    user_request: str
    current_node: str
    node_outputs: dict[str, Any]
    execution_history: list[str]
    validated_plan: dict[str, Any] | None
    artifacts: list[dict[str, Any]]
    validation_results: dict[str, Any] | None
    quality_gate: str | None
    errors: list[str]


class DynamicGraphCompiler:
    """
    Compiles custom visual workflow JSON into executable LangGraph StateGraphs.
    Enforces deterministic GraphContract validation before building the graph,
    and integrates PlanContract, CodeContract, Quality Gate, and Reviewer boundaries.
    """

    def __init__(
        self,
        ollama_client: OllamaClient | None = None,
        workspace_service: WorkspaceService | None = None,
        db: AsyncSession | None = None,
    ) -> None:
        self.client = ollama_client or OllamaClient()
        self.workspace_service = workspace_service
        self.db = db

    def compile(self, graph_json: dict[str, Any]) -> Any:
        """
        Build and compile a StateGraph dynamically from nodes and edges JSON.
        Validates GraphContract before constructing nodes or edges.
        Enforces coding workflow bypass protection.
        """
        # 1. Deterministic Graph Contract Validation
        contract = GraphContractValidator.validate_or_raise(graph_json)

        nodes_list = contract.nodes
        edges_list = contract.edges

        nodes_map = {
            n.id: (n.type.value if hasattr(n.type, "value") else str(n.type).lower())
            for n in nodes_list
        }

        # 2. Coding Workflow Bypass Protection
        has_coder = any(ntype == "coder" for ntype in nodes_map.values())
        has_planner = any(ntype == "planner" for ntype in nodes_map.values())

        if has_coder and not has_planner:
            raise GraphContractValidationError(
                "Coding workflow graph contract violation: A graph with a 'coder' node MUST include a 'planner' node to generate a PlanContract."
            )

        logger.info(
            "Compiling Dynamic LangGraph with %d nodes and %d edges",
            len(nodes_list),
            len(edges_list),
        )

        builder = StateGraph(DynamicAgentState)

        # 3. Add Nodes
        for n in nodes_list:
            node_id = n.id
            node_type = nodes_map[node_id]

            node_fn = self._create_node_handler(node_id, node_type, n.config, nodes_map, edges_list)
            builder.add_node(node_id, node_fn)

        # 4. Add Edges
        first_node_id = nodes_list[0].id
        builder.add_edge(START, first_node_id)

        if edges_list:
            for edge in edges_list:
                builder.add_edge(edge.source, edge.target)
        else:
            for i in range(len(nodes_list) - 1):
                builder.add_edge(nodes_list[i].id, nodes_list[i + 1].id)

        last_node_id = nodes_list[-1].id
        builder.add_edge(last_node_id, END)

        return builder.compile()

    def _get_workspace(self, state: DynamicAgentState) -> WorkspaceService:
        """Resolve session-specific WorkspaceService instance."""
        if self.workspace_service:
            return self.workspace_service

        session_id = state.get("session_id", "default_session")
        return WorkspaceService(db=self.db, session_id=session_id)

    @staticmethod
    def _resolve_upstream_output(
        node_id: str,
        target_type: str,
        state: DynamicAgentState,
        nodes_map: dict[str, str],
        edges_list: list[Any],
    ) -> str:
        """
        Deterministically resolve output from upstream node of target_type.
        Uses graph topology/edges to resolve among multiple candidate nodes of the same agent type.
        Fails deterministically if ambiguous.
        """
        outputs = state.get("node_outputs", {})

        candidates = [nid for nid, ntype in nodes_map.items() if ntype == target_type and nid in outputs]
        if not candidates:
            return ""

        if len(candidates) == 1:
            val = outputs[candidates[0]]
            return val if isinstance(val, str) else str(val)

        # Multiple candidate nodes of target_type exist: check incoming edges to node_id
        upstream_sources = [e.source for e in edges_list if e.target == node_id]
        matching_sources = [nid for nid in candidates if nid in upstream_sources]

        if len(matching_sources) == 1:
            val = outputs[matching_sources[0]]
            return val if isinstance(val, str) else str(val)

        raise ValueError(
            f"Ambiguous upstream node resolution for node '{node_id}' requiring agent type '{target_type}'. "
            f"Multiple matching candidates found: {candidates}. Specify explicit edges."
        )

    def _create_node_handler(
        self,
        node_id: str,
        node_type: str,
        config: dict[str, Any],
        nodes_map: dict[str, str],
        edges_list: list[Any],
    ):
        """Create async node handler closure for given node type."""

        async def _handler(state: DynamicAgentState) -> dict:
            logger.info("Executing Dynamic Graph Node: %s (type=%s)", node_id, node_type)
            outputs = dict(state.get("node_outputs", {}))
            history = list(state.get("execution_history", []))
            history.append(node_id)
            errors = list(state.get("errors", []))
            artifacts = list(state.get("artifacts", []))

            req = state.get("user_request", "")
            ws = self._get_workspace(state)

            val_plan = state.get("validated_plan")
            val_results = state.get("validation_results")
            qg_state = state.get("quality_gate")

            # Check if an earlier deterministic contract failed
            plan_failed = any("PlanContract" in err for err in errors)
            contract_failed = any("CodeContract" in err for err in errors) or qg_state == "FAIL"

            if node_type == "planner":
                agent = PlannerAgent(self.client)
                planner_res = await agent.execute_contract(req)
                if not planner_res.is_valid:
                    err_msg = f"PlanContract rejected: {'; '.join(planner_res.errors)}"
                    errors.append(err_msg)
                    val_plan = None
                    qg_state = "FAIL"
                    res = planner_res.formatted_plan
                else:
                    val_plan = planner_res.contract.model_dump() if planner_res.contract else {}
                    res = planner_res.formatted_plan

            elif node_type == "research":
                if plan_failed:
                    res = "Skipped — PlanContract validation failed"
                else:
                    plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                    agent = ResearchAgent(self.client)
                    res = await agent.execute(req, execution_plan=plan_text)

            elif node_type == "coder":
                if plan_failed:
                    res = "Skipped — PlanContract validation failed"
                else:
                    plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                    research_text = self._resolve_upstream_output(node_id, "research", state, nodes_map, edges_list)
                    agent = CoderAgent(self.client)
                    res = await agent.execute(
                        req,
                        execution_plan=plan_text,
                        research_notes=research_text,
                        workspace_service=ws,
                    )

                    # Inspect workspace files and record artifacts
                    if ws.workspace_dir.exists():
                        for p in ws.workspace_dir.rglob("*.py"):
                            rel_p = str(p.relative_to(ws.workspace_dir))
                            artifacts.append({"path": rel_p, "content": p.read_text(encoding="utf-8")})

                    # Immediate CodeContract Validation
                    code_res = CodeContractValidator.validate(ws.workspace_dir)
                    if not code_res.is_valid:
                        logger.warning("CodeContract FAILED in graph node %s: %s", node_id, code_res.summary)
                        qg_state = "FAIL"
                        err_msg = f"CodeContract Violation: {code_res.summary}"
                        errors.append(err_msg)
                        val_results = {
                            "quality_gate": "FAIL",
                            "code_contract": code_res.model_dump(),
                            "deterministic_checks": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                            "ruff": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                            "pytest": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                            "bandit": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                        }

            elif node_type == "tester":
                if plan_failed or contract_failed:
                    res = "Skipped — Contract boundary validation failed"
                else:
                    coder_code = self._resolve_upstream_output(node_id, "coder", state, nodes_map, edges_list)
                    plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                    agent = TesterAgent(self.client)
                    res_dict = await agent.execute(
                        generated_code=coder_code,
                        execution_plan=plan_text,
                        workspace_service=ws,
                    )
                    res = res_dict["output"]

            elif node_type == "quality_gate":
                if plan_failed or contract_failed:
                    res = f"Quality Gate Executed: FAIL ({'; '.join(errors)})"
                else:
                    det_val = DeterministicValidator()
                    val_results = await det_val.run_full_quality_gate(ws.workspace_dir)
                    qg_state = val_results["quality_gate"]
                    res = f"Quality Gate Execution Completed: {qg_state}"

            elif node_type == "reviewer":
                plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                coder_code = self._resolve_upstream_output(node_id, "coder", state, nodes_map, edges_list)
                tester_text = self._resolve_upstream_output(node_id, "tester", state, nodes_map, edges_list)
                research_text = self._resolve_upstream_output(node_id, "research", state, nodes_map, edges_list)

                # For coding workflows, if Quality Gate was not run as a distinct node, run it automatically
                if "coder" in nodes_map.values() and val_results is None:
                    det_val = DeterministicValidator()
                    val_results = await det_val.run_full_quality_gate(ws.workspace_dir)
                    qg_state = val_results["quality_gate"]

                agent = ReviewerAgent(self.client)
                res_dict = await agent.execute(
                    user_request=req,
                    execution_plan=plan_text,
                    generated_code=coder_code,
                    test_results=tester_text,
                    research_notes=research_text,
                    validation_results=val_results,
                    session_id=state.get("session_id"),
                )
                res = res_dict["output"]
                qg_state = res_dict["quality_gate"]

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
                "validated_plan": val_plan,
                "artifacts": artifacts,
                "validation_results": val_results,
                "quality_gate": qg_state,
                "errors": errors,
            }

        return _handler
