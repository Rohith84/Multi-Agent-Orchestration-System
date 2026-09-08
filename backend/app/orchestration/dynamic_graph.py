"""
Dynamic LangGraph Compiler.

Parses arbitrary graph JSON topologies (nodes, edges, custom agents, conditions) and dynamically constructs executable StateGraph workflows.
Integrates deterministic contract boundaries (PlanContract, CodeContract, Quality Gate, Evidence-Bound Reviewer) into actual graph execution paths.
Preserves structured dynamic agent state (PlanContract, Artifacts, CodeContract, Quality Gate, RAGResult, Errors) across node transitions.
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
import asyncio
import time
from app.schemas.execution_error import ExecutionError, ExecutionErrorType, WorkflowStatus
from app.schemas.execution_trace import ExecutionEvent, ExecutionEventType, ExecutionSummary
from app.core.logging import get_logger

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class DynamicAgentState(TypedDict, total=False):
    """
    Shared dynamic state passed through custom LangGraph workflows.
    Preserves structured deterministic evidence across nodes without unneeded text flattening.
    """

    session_id: str
    user_request: str
    current_node: str
    node_outputs: dict[str, Any]
    execution_history: list[str]
    validated_plan: dict[str, Any] | None
    artifacts: list[dict[str, Any]]
    code_contract: dict[str, Any] | None
    validation_results: dict[str, Any] | None
    quality_gate: str | None
    rag_result: dict[str, Any] | None
    reasoning_metadata: dict[str, Any] | None
    workflow_status: str | None
    execution_errors: list[dict[str, Any]]
    execution_trace: list[dict[str, Any]]
    execution_summary: dict[str, Any] | None
    errors: list[dict[str, Any] | str]


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
            code_contract_data = state.get("code_contract")
            rag_data = state.get("rag_result")

            # Check if an earlier deterministic contract failed
            def _has_err(err_kind: str) -> bool:
                for e in errors:
                    if isinstance(e, dict) and e.get("type") == err_kind:
                        return True
                    if isinstance(e, str) and err_kind in e:
                        return True
                return False

            plan_failed = _has_err("PlanContract") or _has_err("PlanContractError")
            contract_failed = _has_err("CodeContract") or _has_err("CodeContractError") or qg_state in ("CONTRACT_FAILURE", "FAIL")

            sess_id = state.get("session_id") or "default_session"
            trace = list(state.get("execution_trace") or [])
            exec_errors = list(state.get("execution_errors", []))
            wf_status = state.get("workflow_status") or WorkflowStatus.RUNNING.value
            reasoning_dict = dict(state.get("reasoning_metadata") or {})

            def _add_evt(evt_type: ExecutionEventType | str, status: str = "SUCCESS", duration_ms: float | None = None, attempt_num: int | None = None, msg: str | None = None, evidence: dict | None = None):
                evt = ExecutionEvent(
                    session_id=sess_id,
                    event_type=evt_type if isinstance(evt_type, ExecutionEventType) else ExecutionEventType(evt_type),
                    node_id=node_id,
                    agent_type=node_type,
                    status=status,
                    duration_ms=duration_ms,
                    attempt=attempt_num,
                    message=msg,
                    evidence=evidence,
                )
                trace.append(evt.model_dump())

            if not trace:
                evt_wf_start = ExecutionEvent(
                    session_id=sess_id,
                    event_type=ExecutionEventType.WORKFLOW_STARTED,
                    status="SUCCESS",
                    message="Workflow execution started",
                )
                trace.append(evt_wf_start.model_dump())

            attempt = 0
            max_attempts = 2

            while attempt < max_attempts:
                attempt += 1
                start_t = time.time()
                if attempt > 1:
                    _add_evt(ExecutionEventType.NODE_RETRIED, status="RETRYING", attempt_num=attempt, msg=f"Retrying node {node_id}")

                _add_evt(ExecutionEventType.NODE_STARTED, status="RUNNING", attempt_num=attempt)

                try:
                    if node_type == "planner":
                        agent = PlannerAgent(self.client)
                        planner_res = await agent.execute_contract(req)
                        if planner_res.reasoning_metadata:
                            reasoning_dict[node_id] = planner_res.reasoning_metadata.model_dump()
                        if not planner_res.is_valid:
                            err_msg = f"PlanContract rejected: {'; '.join(planner_res.errors)}"
                            errors.append({"node": node_id, "type": "PlanContractError", "message": err_msg})
                            val_plan = None
                            qg_state = "BLOCKED"
                            wf_status = WorkflowStatus.BLOCKED.value
                            res = planner_res.formatted_plan
                            _add_evt(ExecutionEventType.CONTRACT_FAILED, status="CONTRACT_FAILURE", evidence={"contract": "PlanContract", "errors": planner_res.errors})
                        else:
                            val_plan = planner_res.contract.model_dump() if planner_res.contract else {}
                            res = planner_res.formatted_plan
                            _add_evt(ExecutionEventType.CONTRACT_VALIDATED, status="PASS", evidence={"contract": "PlanContract", "subtask_count": len(planner_res.contract.subtasks) if planner_res.contract else 0})

                    elif node_type == "research":
                        if plan_failed:
                            res = "Skipped — PlanContract validation failed"
                            wf_status = WorkflowStatus.BLOCKED.value
                        else:
                            plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                            agent = ResearchAgent(self.client)
                            res, rag_res = await agent.execute_with_result(req, execution_plan=plan_text)
                            rag_data = rag_res.model_dump()
                            rag_stat_str = rag_res.status.value if hasattr(rag_res.status, "value") else str(rag_res.status)
                            _add_evt(ExecutionEventType.RAG_COMPLETED, status=rag_stat_str, evidence={"status": rag_stat_str, "chunks_count": len(rag_res.chunks), "error": rag_res.error})

                    elif node_type == "coder":
                        if plan_failed:
                            res = "Skipped — PlanContract validation failed"
                            wf_status = WorkflowStatus.BLOCKED.value
                        else:
                            plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                            research_text = self._resolve_upstream_output(node_id, "research", state, nodes_map, edges_list)
                            agent = CoderAgent(self.client)
                            res = await agent.execute(
                                req,
                                execution_plan=plan_text,
                                research_notes=research_text,
                                workspace_service=ws,
                                rag_result=rag_data,
                            )

                            if ws.workspace_dir.exists():
                                for p in ws.workspace_dir.rglob("*.py"):
                                    rel_p = str(p.relative_to(ws.workspace_dir))
                                    content = p.read_text(encoding="utf-8")
                                    artifacts.append({
                                        "path": rel_p,
                                        "language": "python",
                                        "status": "persisted",
                                        "size_bytes": len(content),
                                        "content": content,
                                    })

                            code_res = CodeContractValidator.validate(ws.workspace_dir)
                            code_contract_data = code_res.model_dump()
                            if not code_res.is_valid:
                                logger.warning("CodeContract FAILED in graph node %s: %s", node_id, code_res.summary)
                                qg_state = "CONTRACT_FAILURE"
                                wf_status = WorkflowStatus.BLOCKED.value
                                err_msg = f"CodeContract Violation: {code_res.summary}"
                                errors.append({"node": node_id, "type": "CodeContractError", "message": err_msg})
                                val_results = {
                                    "quality_gate": "CONTRACT_FAILURE",
                                    "code_contract": code_contract_data,
                                    "deterministic_checks": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                                    "ruff": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                                    "pytest": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                                    "bandit": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
                                }
                                _add_evt(ExecutionEventType.CONTRACT_FAILED, status="CONTRACT_FAILURE", evidence={"contract": "CodeContract", "summary": code_res.summary})
                            else:
                                _add_evt(ExecutionEventType.CONTRACT_VALIDATED, status="PASS", evidence={"contract": "CodeContract", "summary": code_res.summary})

                    elif node_type == "tester":
                        if plan_failed or contract_failed:
                            res = "Skipped — Contract boundary validation failed"
                            wf_status = WorkflowStatus.BLOCKED.value
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
                            res = f"Quality Gate Executed: {qg_state or 'CONTRACT_FAILURE'}"
                            wf_status = WorkflowStatus.BLOCKED.value
                        else:
                            det_val = DeterministicValidator()
                            _add_evt(ExecutionEventType.TOOL_STARTED, status="RUNNING", msg="Running Quality Gate deterministic tools")
                            val_results = await det_val.run_full_quality_gate(ws.workspace_dir)
                            qg_state = self._classify_detailed_gate_state(val_results)
                            res = f"Quality Gate Execution Completed: {qg_state}"
                            if qg_state in ("FAIL", "CONTRACT_FAILURE", "INFRASTRUCTURE_FAILURE"):
                                wf_status = WorkflowStatus.BLOCKED.value

                            for t_name in ("ruff", "pytest", "bandit"):
                                t_res = val_results.get(t_name)
                                if isinstance(t_res, dict):
                                    t_stat = t_res.get("status", "NOT_EXECUTED")
                                    _add_evt(
                                        ExecutionEventType.TOOL_COMPLETED if t_stat in ("PASS", "FAIL") else ExecutionEventType.TOOL_FAILED,
                                        status=t_stat,
                                        evidence={"tool": t_name, "status": t_stat, "output_snippet": str(t_res.get("output", ""))[:200]},
                                    )

                            _add_evt(ExecutionEventType.QUALITY_GATE_COMPLETED, status=qg_state, evidence={"quality_gate": qg_state, "val_results": val_results})

                    elif node_type == "reviewer":
                        plan_text = self._resolve_upstream_output(node_id, "planner", state, nodes_map, edges_list)
                        coder_code = self._resolve_upstream_output(node_id, "coder", state, nodes_map, edges_list)
                        tester_text = self._resolve_upstream_output(node_id, "tester", state, nodes_map, edges_list)
                        research_text = self._resolve_upstream_output(node_id, "research", state, nodes_map, edges_list)

                        if "coder" in nodes_map.values() and val_results is None:
                            det_val = DeterministicValidator()
                            val_results = await det_val.run_full_quality_gate(ws.workspace_dir)
                            qg_state = self._classify_detailed_gate_state(val_results)
                            _add_evt(ExecutionEventType.QUALITY_GATE_COMPLETED, status=qg_state, evidence={"quality_gate": qg_state, "val_results": val_results})

                        agent = ReviewerAgent(self.client)
                        res_dict = await agent.execute(
                            user_request=req,
                            execution_plan=plan_text,
                            generated_code=coder_code,
                            test_results=tester_text,
                            research_notes=research_text,
                            validation_results=val_results,
                            session_id=state.get("session_id"),
                            rag_result=rag_data,
                        )
                        res = res_dict["output"]
                        if not qg_state or qg_state == "PASS":
                            qg_state = res_dict["quality_gate"]

                        wf_status = WorkflowStatus.COMPLETED.value if qg_state == "PASS" else WorkflowStatus.BLOCKED.value
                        _add_evt(ExecutionEventType.REVIEW_COMPLETED, status=res_dict.get("quality_gate", "NOT_APPROVED"), evidence={"quality_gate": qg_state, "reviewer_output": res[:300]})

                    else:
                        system_prompt = config.get("system_prompt", f"You are node {node_id}.")
                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": req},
                        ]
                        res = await self.client.chat(messages)

                    outputs[node_id] = res
                    node_dur = (time.time() - start_t) * 1000
                    _add_evt(ExecutionEventType.NODE_COMPLETED, status="SUCCESS", duration_ms=node_dur, attempt_num=attempt)
                    break

                except asyncio.CancelledError:
                    node_dur = (time.time() - start_t) * 1000
                    logger.warning("Graph node %s cancelled during attempt %d", node_id, attempt)
                    exec_err = ExecutionError(
                        node=node_id,
                        agent=node_type,
                        error_type=ExecutionErrorType.CANCELLATION,
                        message="Workflow task cancelled during execution",
                        recoverable=False,
                        attempt=attempt,
                    )
                    exec_errors.append(exec_err.model_dump())
                    errors.append(exec_err.model_dump())
                    wf_status = WorkflowStatus.CANCELLED.value
                    if not qg_state or qg_state == "PASS":
                        qg_state = "BLOCKED"
                    res = "Task Cancelled"
                    outputs[node_id] = res
                    _add_evt(ExecutionEventType.NODE_FAILED, status="CANCELLED", duration_ms=node_dur, attempt_num=attempt, msg="Task cancelled")
                    _add_evt(ExecutionEventType.WORKFLOW_CANCELLED, status="CANCELLED")
                    break

                except (asyncio.TimeoutError, TimeoutError) as te:
                    node_dur = (time.time() - start_t) * 1000
                    logger.error("Graph node %s timed out during attempt %d: %s", node_id, attempt, te)
                    if attempt < max_attempts:
                        logger.info("Retrying node %s (attempt %d/%d)", node_id, attempt + 1, max_attempts)
                        continue
                    exec_err = ExecutionError(
                        node=node_id,
                        agent=node_type,
                        error_type=ExecutionErrorType.AGENT_TIMEOUT,
                        message=f"Agent execution timed out: {te}",
                        recoverable=False,
                        attempt=attempt,
                    )
                    exec_errors.append(exec_err.model_dump())
                    errors.append(exec_err.model_dump())
                    wf_status = WorkflowStatus.FAILED.value
                    qg_state = "INFRASTRUCTURE_FAILURE"
                    res = f"Execution Error: Node {node_id} timed out"
                    outputs[node_id] = res
                    _add_evt(ExecutionEventType.NODE_FAILED, status="FAILED", duration_ms=node_dur, attempt_num=attempt, msg=str(te))
                    _add_evt(ExecutionEventType.WORKFLOW_FAILED, status="FAILED", msg="Agent timeout")
                    break

                except (IOError, OSError) as os_err:
                    node_dur = (time.time() - start_t) * 1000
                    logger.error("Workspace/IO failure in node %s attempt %d: %s", node_id, attempt, os_err)
                    exec_err = ExecutionError(
                        node=node_id,
                        agent=node_type,
                        error_type=ExecutionErrorType.WORKSPACE_FAILURE,
                        message=str(os_err),
                        recoverable=False,
                        attempt=attempt,
                    )
                    exec_errors.append(exec_err.model_dump())
                    errors.append(exec_err.model_dump())
                    wf_status = WorkflowStatus.FAILED.value
                    qg_state = "INFRASTRUCTURE_FAILURE"
                    res = f"Workspace Failure: {os_err}"
                    outputs[node_id] = res
                    _add_evt(ExecutionEventType.NODE_FAILED, status="FAILED", duration_ms=node_dur, attempt_num=attempt, msg=str(os_err))
                    _add_evt(ExecutionEventType.WORKFLOW_FAILED, status="FAILED", msg="Workspace failure")
                    break

                except Exception as exc:
                    node_dur = (time.time() - start_t) * 1000
                    logger.error("Unhandled exception in graph node %s attempt %d: %s", node_id, attempt, exc)
                    is_transient = "timeout" in str(exc).lower() or "connection" in str(exc).lower()
                    if is_transient and attempt < max_attempts:
                        logger.info("Retrying node %s on transient error (attempt %d/%d)", node_id, attempt + 1, max_attempts)
                        continue
                    exec_err = ExecutionError(
                        node=node_id,
                        agent=node_type,
                        error_type=ExecutionErrorType.AGENT_FAILURE,
                        message=str(exc),
                        recoverable=False,
                        attempt=attempt,
                    )
                    exec_errors.append(exec_err.model_dump())
                    errors.append(exec_err.model_dump())
                    wf_status = WorkflowStatus.FAILED.value
                    qg_state = "INFRASTRUCTURE_FAILURE"
                    res = f"Execution Error: {exc}"
                    outputs[node_id] = res
                    _add_evt(ExecutionEventType.NODE_FAILED, status="FAILED", duration_ms=node_dur, attempt_num=attempt, msg=str(exc))
                    _add_evt(ExecutionEventType.WORKFLOW_FAILED, status="FAILED", msg=str(exc))
                    break

            if wf_status == WorkflowStatus.COMPLETED.value:
                _add_evt(ExecutionEventType.WORKFLOW_COMPLETED, status="COMPLETED")
            elif wf_status == WorkflowStatus.BLOCKED.value:
                _add_evt(ExecutionEventType.WORKFLOW_BLOCKED, status="BLOCKED")

            # Derive ExecutionSummary
            summary = ExecutionSummary(
                session_id=sess_id,
                workflow_status=wf_status,
                duration_ms=sum(e.get("duration_ms") or 0.0 for e in trace),
                nodes_executed=len(set(e.get("node_id") for e in trace if e.get("node_id"))),
                nodes_failed=sum(1 for e in trace if e.get("event_type") == ExecutionEventType.NODE_FAILED.value),
                retries=sum(1 for e in trace if e.get("event_type") == ExecutionEventType.NODE_RETRIED.value),
                contract_results={
                    "plan": "VALID" if val_plan else ("INVALID" if plan_failed else "NOT_CHECKED"),
                    "code": code_contract_data.get("summary", "NOT_CHECKED") if isinstance(code_contract_data, dict) else ("VALID" if code_contract_data else "NOT_CHECKED"),
                },
                rag_status=rag_data.get("status") if isinstance(rag_data, dict) else None,
                quality_gate=qg_state,
                reviewer_decision=qg_state if (qg_state and qg_state != "INFRASTRUCTURE_FAILURE") else "NOT_APPROVED",
                errors=exec_errors,
            ).model_dump()

            return {
                "current_node": node_id,
                "node_outputs": outputs,
                "execution_history": history,
                "validated_plan": val_plan,
                "artifacts": artifacts,
                "code_contract": code_contract_data,
                "validation_results": val_results,
                "quality_gate": qg_state,
                "rag_result": rag_data,
                "reasoning_metadata": reasoning_dict,
                "workflow_status": wf_status,
                "execution_errors": exec_errors,
                "execution_trace": trace,
                "execution_summary": summary,
                "errors": errors,
            }

        return _handler

    @staticmethod
    def _classify_detailed_gate_state(val_results: dict[str, Any]) -> str:
        """Preserve detailed authoritative Quality Gate state without unneeded flattening."""
        gate = val_results.get("quality_gate", "FAIL")
        if gate != "FAIL":
            return gate

        # Check for specific failure categories
        code_cc = val_results.get("code_contract", {})
        if code_cc and not code_cc.get("is_valid", True):
            return "CONTRACT_FAILURE"

        pytest_st = val_results.get("pytest", {}).get("status")
        if pytest_st == "FAIL":
            return "TEST_FAILURE"

        ruff_st = val_results.get("ruff", {}).get("status")
        if ruff_st == "FAIL":
            return "LINT_FAILURE"

        if pytest_st == "ERROR" or ruff_st == "ERROR" or val_results.get("workspace_validation", {}).get("status") == "ERROR":
            return "INFRASTRUCTURE_FAILURE"

        return "FAIL"
