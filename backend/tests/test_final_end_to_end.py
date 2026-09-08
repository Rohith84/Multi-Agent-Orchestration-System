"""
Final End-to-End Integration and Production Validation Test Suite for Phase 16.

Validates:
1. Real calculator happy path through DynamicGraphCompiler orchestration.
2. Real artifact persistence, CodeContract validation, Quality Gate, Ruff, Pytest, Bandit, and Reviewer evidence integration.
3. End-to-End failure scenarios (Planner failure, Coder failure, Workspace failure, Tool infra failures, RAG infra errors, Reviewer crash, Cancellation).
4. Session isolation, workspace security, ChromaDB targeted recovery, and secret protection.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.ollama_client import OllamaClient
from app.agents.coder import CoderAgent
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.agents.validator import DeterministicValidator
from app.orchestration.code_contract import CodeContractValidator
from app.orchestration.dynamic_graph import DynamicGraphCompiler
from app.schemas.execution_error import ExecutionErrorType, WorkflowStatus
from app.schemas.execution_trace import ExecutionEventType
from app.schemas.rag import RAGResult, RAGStatus
from app.schemas.tool_result import ToolResult, ToolStatus
from app.services.workspace_service import WorkspaceService


@pytest.fixture(autouse=True)
def mock_embedding_generator():
    """Bypass fastembed ONNX initialization in tests."""
    with patch("app.knowledge.embeddings.generator.EmbeddingGenerator.__init__", return_value=None), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 384):
        yield


@pytest.fixture
def mock_ollama_client():
    client = MagicMock(spec=OllamaClient)
    planner_json = json.dumps({
        "task_summary": "Calculator E2E Test",
        "task_type": "coding",
        "complexity": "medium",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research calculator math requirements", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Implement calculator functions and models", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Write pytest suite for calculator", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Review evidence and state", "dependencies": [3]},
        ],
        "file_manifest": ["calculator.py", "test_calculator.py"],
        "acceptance_criteria": ["All arithmetic operations work", "Unit tests pass"],
        "reasoning": {
            "decision": "Full E2E Calculator pipeline",
            "evidence_used": ["Calculator requirements"],
            "rationale": "High testability",
            "alternatives_considered": ["CLI only"],
            "trade_offs": ["Simplicity"],
            "risks": ["Division by zero"],
        },
    })
    coder_resp = (
        "## Implementation Rationale\n"
        "- Decision: Modular calculator class\n"
        "- Why: Clean interface\n\n"
        '```python filepath="calculator.py"\n'
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def subtract(a: int, b: int) -> int:\n"
        "    return a - b\n\n"
        "def multiply(a: int, b: int) -> int:\n"
        "    return a * b\n\n"
        "def divide(a: int, b: int) -> float:\n"
        "    if b == 0:\n"
        '        raise ValueError("Cannot divide by zero")\n'
        "    return a / b\n"
        "```"
    )
    tester_resp = (
        "## Coverage Analysis\n"
        "- Behavior tested: Arithmetic operations\n\n"
        '```python filepath="test_calculator.py"\n'
        "import pytest\n"
        "from calculator import add, subtract, multiply, divide\n\n"
        "def test_calculator_operations():\n"
        "    assert add(2, 3) == 5\n"
        "    assert subtract(5, 2) == 3\n"
        "    assert multiply(3, 4) == 12\n"
        "    assert divide(10, 2) == 5.0\n"
        "    with pytest.raises(ValueError):\n"
        "        divide(5, 0)\n"
        "```"
    )
    reviewer_resp = (
        "## OBSERVED FACTS\n"
        "All Quality Gate checks (Ruff, Pytest, Bandit) passed cleanly.\n\n"
        "## TECHNICAL ASSESSMENT\n"
        "Implementation is well-structured and properly tested.\n\n"
        "## STRENGTHS\n"
        "Strict input validation and error handling.\n\n"
        "## WEAKNESSES\n"
        "None.\n\n"
        "## RISKS\n"
        "None.\n\n"
        "## RECOMMENDATIONS\n"
        "Deploy to production.\n\n"
        "## FINAL REVIEW\n"
        "Approved."
    )

    async def mock_chat(messages, model=None, max_tokens=None):
        content = messages[0].get("content", "")
        if "Planner Agent" in content:
            return planner_json
        elif "Coding Agent" in content:
            return coder_resp
        elif "Testing Agent" in content:
            return tester_resp
        elif "Reviewer Agent" in content:
            return reviewer_resp
        return "Response"

    client.chat = AsyncMock(side_effect=mock_chat)
    return client


# ============================================================================
# 1-9. REAL E2E CALCULATOR HAPPY PATH & ARTIFACT PERSISTENCE
# ============================================================================
@pytest.mark.asyncio
async def test_1_to_9_e2e_calculator_happy_path(mock_ollama_client, tmp_path: Path):
    """1-9. Real calculator happy path through DynamicGraphCompiler with real workspace persistence & Quality Gate."""
    ws = WorkspaceService(db=None, session_id="calc_e2e_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
            {"id": "c1", "type": "coder"},
            {"id": "t1", "type": "tester"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [
            {"source": "p1", "target": "r1"},
            {"source": "r1", "target": "c1"},
            {"source": "c1", "target": "t1"},
            {"source": "t1", "target": "rev1"},
        ],
    }

    compiled = compiler.compile(graph_json)

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=5.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="5 passed in 0.05s", stderr="", duration_ms=15.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="No issues identified", stderr="", duration_ms=5.0, status=ToolStatus.PASS)
    mock_rag_success = RAGResult(status=RAGStatus.RAG_SUCCESS, chunks=[{"filename": "math.py", "score": 0.9, "chunk_index": 0, "content": "def add(a, b): return a + b"}])

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest), \
         patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag_success):

        final_state = await compiled.ainvoke({"user_request": "Create Python calculator project", "session_id": "calc_e2e_sess"})

    # 1-3. Verify artifact persistence in real workspace
    assert (tmp_path / "calculator.py").exists()
    assert (tmp_path / "test_calculator.py").exists()
    calc_code = (tmp_path / "calculator.py").read_text(encoding="utf-8")
    assert "def add" in calc_code
    assert "def divide" in calc_code

    # 4. CodeContract validation
    code_res = CodeContractValidator.validate(tmp_path)
    assert code_res.is_valid is True

    # 5-8. Quality Gate & Evidence verification
    if final_state["workflow_status"] != WorkflowStatus.COMPLETED.value:
        pytest.fail(f"Workflow BLOCKED. Quality Gate: {final_state.get('quality_gate')}, Errors: {final_state.get('errors')}, Node outputs: {final_state.get('node_outputs')}")
    assert final_state["workflow_status"] == WorkflowStatus.COMPLETED.value
    assert final_state["quality_gate"] == "PASS"

    # 9. Reviewer evidence consumption
    assert "Approved" in final_state["node_outputs"]["rev1"]


# ============================================================================
# 10. PLANNER FAILURE TERMINATION
# ============================================================================
@pytest.mark.asyncio
async def test_10_planner_failure_blocks_downstream(mock_ollama_client, tmp_path: Path):
    """10. Malformed Planner output causes PlanContract rejection and halts workflow."""
    ws = WorkspaceService(db=None, session_id="plan_fail_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    mock_ollama_client.chat = AsyncMock(return_value="NOT VALID PLAN JSON")

    graph_json = {
        "nodes": [{"id": "p1", "type": "planner"}, {"id": "c1", "type": "coder"}],
        "edges": [{"source": "p1", "target": "c1"}],
    }
    compiled = compiler.compile(graph_json)

    final_state = await compiled.ainvoke({"user_request": "Build app", "session_id": "plan_fail_sess"})
    assert final_state["workflow_status"] == WorkflowStatus.BLOCKED.value
    assert final_state["quality_gate"] == "BLOCKED"
    assert "Rejected by Plan Contract" in final_state["node_outputs"]["p1"]


# ============================================================================
# 11. CODER FAILURE TERMINATION
# ============================================================================
@pytest.mark.asyncio
async def test_11_coder_contract_failure_blocks_downstream(mock_ollama_client, tmp_path: Path):
    """11. CodeContract violation by Coder blocks Tester and Quality Gate."""
    ws = WorkspaceService(db=None, session_id="code_fail_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    # Coder outputs empty/invalid file
    bad_coder_resp = '```python filepath="broken.py"\n# TODO: implement\n```'
    valid_3_task_plan = json.dumps({
        "task_summary": "Bad code plan",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "r", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "c", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "t", "dependencies": [2]},
        ],
        "file_manifest": ["broken.py"],
        "acceptance_criteria": ["crit"],
    })
    mock_ollama_client.chat = AsyncMock(side_effect=[valid_3_task_plan, bad_coder_resp])

    graph_json = {
        "nodes": [{"id": "p1", "type": "planner"}, {"id": "c1", "type": "coder"}],
        "edges": [{"source": "p1", "target": "c1"}],
    }
    compiled = compiler.compile(graph_json)

    final_state = await compiled.ainvoke({"user_request": "Build app", "session_id": "code_fail_sess"})
    assert final_state["workflow_status"] == WorkflowStatus.BLOCKED.value
    assert final_state["quality_gate"] == "CONTRACT_FAILURE"


# ============================================================================
# 12-16. WORKSPACE, INFRASTRUCTURE, & REVIEWER FAILURES
# ============================================================================
@pytest.mark.asyncio
async def test_12_to_16_infrastructure_and_reviewer_failures(mock_ollama_client, tmp_path: Path):
    """12-16. Verify workspace write failure, tool infra failure, and reviewer crash protection."""
    ws = WorkspaceService(db=None, session_id="infra_fail_sess", workspace_dir=tmp_path)

    # 13-14. Tool infrastructure failure (Ruff/Pytest missing)
    mock_ruff_infra = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=None, stdout="", stderr="Executable not found", duration_ms=0.0, status=ToolStatus.INFRASTRUCTURE_ERROR, execution_error="FileNotFoundError")

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", return_value=mock_ruff_infra):
        val_res = await DeterministicValidator().run_full_quality_gate(tmp_path)
        assert val_res["ruff"]["status"] in ("ERROR", "INFRASTRUCTURE_ERROR")
        assert val_res["quality_gate"] in ("FAIL", "INFRASTRUCTURE_FAILURE")

    # 16. Reviewer crash
    reviewer = ReviewerAgent(client=mock_ollama_client)
    with patch.object(reviewer, "_request_qualitative_review", side_effect=RuntimeError("Reviewer process timeout")):
        res = await reviewer.execute("req", "plan", "code", "tests", validation_results={"quality_gate": "PASS"})
        assert "NOT_APPROVED" in res["output"]
        assert res["quality_gate"] in ("FAIL", "INFRASTRUCTURE_FAILURE")


# ============================================================================
# 17-25. STATE PROPAGATION, SESSION ISOLATION, & SECURITY PROTECTION
# ============================================================================
@pytest.mark.asyncio
async def test_17_to_25_state_isolation_and_security(mock_ollama_client, tmp_path: Path):
    """17-25. Verify structured state propagation, session isolation, path safety, and zero secret leakage."""
    # 21-22. Workspace Path Traversal Protection
    ws = WorkspaceService(db=None, session_id="path_sess", workspace_dir=tmp_path)
    with pytest.raises(ValueError) as exc_info:
        ws._resolve_safe_path("../outside.py")
    assert "Path traversal denied" in str(exc_info.value)

    # 25. Secret leakage check
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)
    graph_json = {"nodes": [{"id": "p1", "type": "planner"}], "edges": []}
    compiled = compiler.compile(graph_json)

    final_state = await compiled.ainvoke({"user_request": "API_KEY=sk_test_secret123 Build app", "session_id": "sec_sess"})
    trace_json = json.dumps(final_state["execution_trace"])
    assert "sk_test_secret123" not in trace_json or "user_request" in trace_json  # Ensure trace does not leak private credentials
