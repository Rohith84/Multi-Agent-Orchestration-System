"""
LangGraph orchestration graph builder with Autonomous Self-Repair Loop and Dynamic Routing.

Defines the shared state and builds the state graph workflow:
START -> Planner -> (Dynamic Routing) -> Research -> Coder -> Tester -> Validator (Quality Gate) -> (Repair Loop) -> Reviewer -> END

Flow after refactor:
  Coder generates code → Tester generates tests → Quality Gate runs Ruff/Pytest/Bandit
  → Repair loop if validation fails → Reviewer provides qualitative assessment.
"""

from typing import TypedDict, Any
import time
import re
from langgraph.graph import StateGraph, START, END

from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.coder import CoderAgent
from app.agents.tester import TesterAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.validator import DeterministicValidator
from app.orchestration.plan_validator import PlanContractValidator
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
    tester_analysis: str
    validation_results: dict[str, Any]
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

        # Deterministic Plan Contract Validation — reject out-of-bound or duplicate plans immediately
        plan_res = PlanContractValidator.validate(output)
        if not plan_res.is_valid:
            error_msg = f"Plan Contract Violation: {'; '.join(plan_res.errors)}"
            logger.error("Rejecting plan before downstream execution: %s", error_msg)
            return {
                "execution_plan": f"### Plan Validation Error (Rejected by Plan Contract)\n{error_msg}\n\nOriginal Output:\n{output}",
                "required_agents": ["reviewer"],
                "current_agent": "planner",
                "errors": plan_res.errors,
                "repair_attempts": 0,
                "test_passed": False,
                "execution_time": round(time.perf_counter() - started, 3),
            }
        
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

        # Determine if task requires research / coding — using word boundary regex to avoid false substring matches
        req_text = state["user_request"].lower()
        has_coding_keyword = bool(re.search(
            r'\b(build|create|implement|app|application|dashboard|write|develop|system|feature|ui|api|database|coding)\b',
            req_text
        ))
        is_coding_or_app_task = "coder" in required_agents or has_coding_keyword

        if is_coding_or_app_task:
            # Enforce full agent sequence for coding/build tasks: research -> coder -> tester -> reviewer
            if "research" not in required_agents:
                logger.info("Orchestration rule: Enforcing 'research' agent before 'coder' for coding/build task")
                required_agents.insert(0, "research")
            if "coder" not in required_agents:
                required_agents.append("coder")
            if "tester" not in required_agents:
                required_agents.append("tester")
            if "reviewer" not in required_agents:
                required_agents.append("reviewer")
        elif "research" in output.lower() and "research" not in required_agents:
            required_agents.insert(0, "research")
            
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
        try:
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
        except Exception as exc:
            logger.error("Research Agent execution failed: %s", exc, exc_info=True)
            error_notes = (
                "==================================================\n"
                "RESEARCH SUMMARY (FAILED)\n"
                "==================================================\n"
                f"ERROR: Research Agent failed during execution: {exc}\n"
                "Downstream Coder Agent must proceed with caution using fallback requirements."
            )
            return {
                "research_notes": error_notes,
                "errors": state.get("errors", []) + [f"Research Agent failed: {exc}"],
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
        """Tester generates test scripts and analyzes coverage. Does NOT execute tests."""
        logger.info("LangGraph Node: Tester (test generation & coverage analysis)")
        started = time.perf_counter()
        tool_runner = MCPToolRunner("tester")
        res = await tester.execute(
            generated_code=state["generated_code"],
            execution_plan=state["execution_plan"],
            workspace_service=workspace_service,
            tool_runner=tool_runner,
            validation_results=state.get("validation_results"),
        )
        return {
            "test_results": res["output"],
            "tester_analysis": res.get("tester_analysis", ""),
            "current_agent": "tester",
            "execution_time": round(time.perf_counter() - started, 3),
        }

    async def validator_node(state: AgentState) -> dict:
        """Full Quality Gate: syntax/imports/manifest + Ruff + Pytest + Bandit."""
        logger.info("LangGraph Node: Quality Gate (full deterministic validation)")
        started = time.perf_counter()
        det_validator = DeterministicValidator()

        sandbox_dir = workspace_service.workspace_dir if workspace_service else None
        if not sandbox_dir or not sandbox_dir.exists():
            logger.warning("Quality Gate: no workspace directory available — FAIL (missing evidence)")
            return {
                "test_passed": False,
                "quality_gate": "FAIL",
                "validation_results": {
                    "deterministic_checks": {"status": "ERROR", "output": "No workspace directory"},
                    "ruff": {"status": "ERROR", "output": "Skipped"},
                    "pytest": {"status": "ERROR", "output": "Skipped"},
                    "bandit": {"status": "ERROR", "output": "Skipped"},
                    "quality_gate": "FAIL",
                    "test_passed": False,
                },
                "current_agent": "validator",
                "execution_time": round(time.perf_counter() - started, 3),
            }

        # Run the full Quality Gate (syntax + ruff + pytest + bandit)
        validation_results = await det_validator.run_full_quality_gate(sandbox_dir)
        quality_gate = validation_results["quality_gate"]
        test_passed = validation_results["test_passed"]

        if not test_passed:
            attempts = state.get("repair_attempts", 0) + 1
            logger.info(
                "Quality Gate FAILED (quality_gate=%s, repair attempt %d/3)",
                quality_gate,
                attempts,
            )

            # Build bug report from validation errors for repair loop
            det_output = validation_results.get("deterministic_checks", {}).get("output", "")
            ruff_output = validation_results.get("ruff", {}).get("output", "")
            pytest_output = validation_results.get("pytest", {}).get("output", "")
            combined_errors = f"{det_output}\n{ruff_output}\n{pytest_output}"

            return {
                "test_passed": False,
                "quality_gate": quality_gate,
                "validation_results": validation_results,
                "test_results": f"QUALITY GATE FAILED:\n{combined_errors[:2000]}",
                "bug_report": {
                    "failed_file": "workspace",
                    "failed_test": "quality_gate",
                    "stack_trace": combined_errors[:1500],
                    "error_category": "QualityGateFailure",
                    "suggested_fix": "Fix the issues reported by the Quality Gate (syntax errors, linting issues, test failures).",
                    "severity": "CRITICAL",
                },
                "repair_attempts": attempts,
                "current_agent": "validator",
                "execution_time": round(time.perf_counter() - started, 3),
            }

        logger.info("Quality Gate PASSED (quality_gate=%s)", quality_gate)
        return {
            "test_passed": True,
            "quality_gate": quality_gate,
            "validation_results": validation_results,
            "current_agent": "validator",
            "execution_time": round(time.perf_counter() - started, 3),
        }

    async def reviewer_node(state: AgentState) -> dict:
        """Reviewer consumes pre-computed Quality Gate results for qualitative assessment."""
        logger.info("LangGraph Node: Reviewer (qualitative review)")
        started = time.perf_counter()
        try:
            tool_runner = MCPToolRunner("reviewer")
            res = await reviewer.execute(
                user_request=state["user_request"],
                execution_plan=state["execution_plan"],
                generated_code=state["generated_code"],
                test_results=state.get("test_results", ""),
                research_notes=state.get("research_notes", ""),
                validation_results=state.get("validation_results"),
                tester_analysis=state.get("tester_analysis", ""),
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
            # On crash, fail closed — do not default to PASS
            return {
                "review": f"[Reviewer Error] {exc}. Code was generated but could not be reviewed.",
                "quality_gate": state.get("quality_gate", "FAIL"),
                "overall_score": 0.0,
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
        """After Coder, route to Tester (to generate tests before Quality Gate)."""
        req_agents = state.get("required_agents", [])
        if "tester" in req_agents:
            return "tester"
        if "reviewer" in req_agents:
            return "reviewer"
        return "end"

    def route_after_tester(state: AgentState) -> str:
        """After Tester generates tests, route to Quality Gate."""
        req_agents = state.get("required_agents", [])
        # Always route to validator (Quality Gate) after tester
        return "validator"

    def route_after_validator(state: AgentState) -> str:
        """Route based on Quality Gate results. Fail-closed defaults."""
        req_agents = state.get("required_agents", [])
        # If Quality Gate failed, loop back to coder for repair (max 3 attempts)
        if not state.get("test_passed", False) and state.get("repair_attempts", 0) < 3:
            logger.info("Quality Gate failed — routing back to Coder for repair (attempt %d/3)", state.get("repair_attempts"))
            return "coder"
        if not state.get("test_passed", False):
            logger.info("Quality Gate still failing after 3 repair attempts — proceeding to reviewer")
        # Quality Gate passed (or max retries) — proceed to reviewer
        if "reviewer" in req_agents:
            return "reviewer"
        return "end"

    builder = StateGraph(AgentState)
    builder.add_node("planner", planner_node)
    builder.add_node("research", research_node)
    builder.add_node("coder", coder_node)
    builder.add_node("tester", tester_node)
    builder.add_node("validator", validator_node)
    builder.add_node("reviewer", reviewer_node)

    valid_starts = {"planner", "research", "coder", "tester", "validator", "reviewer"}
    if start_at not in valid_starts:
        raise ValueError(f"Unknown workflow resume agent: {start_at}")

    builder.add_edge(START, start_at)
    
    # Conditional edges for dynamic routing
    # Flow: Planner → Research → Coder → Tester → Validator (Quality Gate) → Reviewer
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
    builder.add_conditional_edges("tester", route_after_tester, {
        "validator": "validator",
    })
    builder.add_conditional_edges("validator", route_after_validator, {
        "coder": "coder",
        "reviewer": "reviewer",
        "end": END
    })
    builder.add_edge("reviewer", END)

    return builder.compile()
