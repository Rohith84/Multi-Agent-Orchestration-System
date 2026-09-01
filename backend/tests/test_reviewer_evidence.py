"""
Unit tests for Phase 7: Evidence-Bound Reviewer.

Validates that ReviewerAgent:
- Consumes structured evidence from ToolResult, CodeContractResult, and RAGResult
- Never claims lint/test errors on INFRASTRUCTURE_ERROR (FileNotFoundError, TimeoutExpired, etc.)
- Does not infer ToolStatus from raw "Tool execution error" strings without structured evidence
- Reports CONTRACT_FAILURE with exact rules
- Distinguishes RAG_SUCCESS, RAG_EMPTY, and RAG_INFRASTRUCTURE_ERROR
- Marks missing structured evidence as UNAVAILABLE
- Preserves raw outputs without mutation
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.reviewer import ReviewerAgent
from app.ai.ollama_client import OllamaClient
from app.schemas.tool_result import ToolResult, ToolStatus


@pytest.fixture
def mock_ollama_client():
    client = MagicMock(spec=OllamaClient)
    client.chat = AsyncMock(return_value="### Review Summary\nCode reviewed against evidence.\n\n### Quality Score\n85/100\n\n### Final Status\nAPPROVED\n")
    return client


@pytest.mark.asyncio
async def test_1_ruff_pass_evidence(mock_ollama_client):
    """1. Ruff PASS → Reviewer receives PASS evidence."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "PASS",
        "ruff": {
            "status": "PASS",
            "output": "All checks passed cleanly.",
            "result": ToolResult(
                tool="ruff",
                command=["ruff", "check", "."],
                cwd="/tmp",
                exit_code=0,
                stdout="All checks passed cleanly.",
                stderr="",
                duration_ms=45.0,
                status=ToolStatus.PASS,
            ).model_dump(),
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Ruff Linter Status: PASS" in res["output"]
    assert "Exit Code 0" in res["output"]


@pytest.mark.asyncio
async def test_2_ruff_lint_failure_evidence(mock_ollama_client):
    """2. Ruff LINT_FAILURE with actual output → Reviewer can reference actual lint evidence."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "ruff": {
            "status": "FAIL",
            "output": "main.py:10:1: F821 Undefined name 'x'",
            "result": ToolResult(
                tool="ruff",
                command=["ruff", "check", "."],
                cwd="/tmp",
                exit_code=1,
                stdout="main.py:10:1: F821 Undefined name 'x'",
                stderr="",
                duration_ms=50.0,
                status=ToolStatus.LINT_FAILURE,
            ).model_dump(),
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Ruff Linter Status: LINT_FAILURE" in res["output"]
    assert "F821 Undefined name 'x'" in res["output"]


@pytest.mark.asyncio
async def test_3_ruff_infrastructure_error_cannot_claim_lint_violations(mock_ollama_client):
    """3. Ruff INFRASTRUCTURE_ERROR → Reviewer cannot claim lint violations."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "ruff": {
            "status": "ERROR",
            "output": "Tool not installed",
            "result": ToolResult(
                tool="ruff",
                command=["ruff", "check"],
                cwd="/tmp",
                exit_code=None,
                stdout="",
                stderr="",
                execution_error="FileNotFoundError: ruff binary missing",
                duration_ms=2.0,
                status=ToolStatus.INFRASTRUCTURE_ERROR,
            ).model_dump(),
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Ruff Linter Status: INFRASTRUCTURE_ERROR" in res["output"]
    assert "Code quality or defects cannot be evaluated from this tool" in res["output"]
    assert "style violations" not in res["output"].lower()


@pytest.mark.asyncio
async def test_4_pytest_pass_evidence(mock_ollama_client):
    """4. Pytest PASS → Reviewer receives PASS evidence."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "PASS",
        "pytest": {
            "status": "PASS",
            "output": "5 passed in 0.5s",
            "result": ToolResult(
                tool="pytest",
                command=["pytest"],
                cwd="/tmp",
                exit_code=0,
                stdout="5 passed in 0.5s",
                stderr="",
                duration_ms=500.0,
                status=ToolStatus.PASS,
            ).model_dump(),
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Pytest Execution Status: PASS" in res["output"]


@pytest.mark.asyncio
async def test_5_pytest_test_failure_evidence(mock_ollama_client):
    """5. Pytest TEST_FAILURE with actual failure output → Reviewer can reference actual test failure."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "pytest": {
            "status": "FAIL",
            "output": "FAILED test_calculator.py::test_add - AssertionError: assert 2 == 3",
            "result": ToolResult(
                tool="pytest",
                command=["pytest"],
                cwd="/tmp",
                exit_code=1,
                stdout="FAILED test_calculator.py::test_add - AssertionError: assert 2 == 3",
                stderr="",
                duration_ms=400.0,
                status=ToolStatus.TEST_FAILURE,
            ).model_dump(),
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Pytest Execution Status: TEST_FAILURE" in res["output"]
    assert "AssertionError: assert 2 == 3" in res["output"]


@pytest.mark.asyncio
async def test_6_7_8_pytest_infrastructure_error(mock_ollama_client):
    """
    6. Pytest INFRASTRUCTURE_ERROR → Reviewer cannot claim tests failed.
    7. FileNotFoundError is infrastructure failure.
    8. TimeoutExpired is infrastructure failure.
    """
    reviewer = ReviewerAgent(mock_ollama_client)
    for exc_msg in ["FileNotFoundError: pytest binary missing", "TimeoutExpired: pytest timed out after 30s"]:
        val_results = {
            "quality_gate": "FAIL",
            "pytest": {
                "status": "ERROR",
                "output": exc_msg,
                "result": ToolResult(
                    tool="pytest",
                    command=["pytest"],
                    cwd="/tmp",
                    exit_code=None,
                    stdout="",
                    stderr="",
                    execution_error=exc_msg,
                    duration_ms=3000.0,
                    status=ToolStatus.INFRASTRUCTURE_ERROR,
                ).model_dump(),
            },
        }
        res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

        assert "Pytest Execution Status: INFRASTRUCTURE_ERROR" in res["output"]
        assert "Code quality or defects cannot be evaluated from this tool" in res["output"]


@pytest.mark.asyncio
async def test_9_code_contract_valid(mock_ollama_client):
    """9. CodeContract VALID → Reviewer receives VALID evidence."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "PASS",
        "code_contract": {"status": "VALID", "is_valid": True, "errors": [], "summary": "All contract checks passed."},
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "CodeContract Status: VALID" in res["output"]


@pytest.mark.asyncio
async def test_10_code_contract_failure_reports_actual_rules(mock_ollama_client):
    """10. CodeContract CONTRACT_FAILURE → Reviewer reports actual contract violation."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "code_contract": {
            "status": "CONTRACT_FAILURE",
            "is_valid": False,
            "summary": "1 violation detected.",
            "errors": [{"file": "main.py", "line": 5, "rule": "CONCRETE_FUNCTION_PASS", "message": "Function containing only pass"}],
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "CodeContract Status: CONTRACT_FAILURE" in res["output"]
    assert "CONCRETE_FUNCTION_PASS" in res["output"]
    assert "main.py:5" in res["output"]


@pytest.mark.asyncio
async def test_11_12_13_rag_evidence_handling(mock_ollama_client):
    """
    11. RAG_SUCCESS → Reviewer can use retrieved evidence.
    12. RAG_EMPTY → Reviewer distinguishes empty retrieval from failure.
    13. RAG_INFRASTRUCTURE_ERROR → Reviewer does not claim no documents exist.
    """
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {"quality_gate": "PASS"}

    # 11. RAG_SUCCESS
    res_success = await reviewer.execute("req", "plan", "code", "tests", research_notes="Status: RAG_SUCCESS\nRetrieved docs.", validation_results=val_results)
    assert "RAG Status: RAG_SUCCESS" in res_success["output"]

    # 12. RAG_EMPTY
    res_empty = await reviewer.execute("req", "plan", "code", "tests", research_notes="Status: RAG_EMPTY\nreturned 0 relevant document chunks", validation_results=val_results)
    assert "RAG Status: RAG_EMPTY" in res_empty["output"]

    # 13. RAG_INFRASTRUCTURE_ERROR
    res_infra = await reviewer.execute("req", "plan", "code", "tests", research_notes="Status: RAG_INFRASTRUCTURE_ERROR\nERROR: Knowledge Base retrieval failed due to an infrastructure error: Connection refused", validation_results=val_results)
    assert "RAG Status: RAG_INFRASTRUCTURE_ERROR" in res_infra["output"]
    assert "Do NOT claim no documents exist" in res_infra["output"]



@pytest.mark.asyncio
async def test_14_generic_tool_execution_error_string_not_inferred_as_lint_failure(mock_ollama_client):
    """14. Generic 'Tool execution error' string must not be converted into a fabricated lint/test explanation without structured status."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "ruff": {
            "output": "Tool execution error: RuntimeError: spawn failed",
            # No structured 'result' dict, and status is None
        },
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Ruff Linter Status: UNAVAILABLE" in res["output"]


@pytest.mark.asyncio
async def test_15_16_mixed_results(mock_ollama_client):
    """
    15. Mixed results: Ruff PASS + Pytest INFRASTRUCTURE_ERROR → Reviewer must not claim gate failed due to code defects.
    16. Mixed results: Ruff LINT_FAILURE + Pytest PASS → Reviewer reports lint failure only.
    """
    reviewer = ReviewerAgent(mock_ollama_client)

    # 15. Ruff PASS + Pytest INFRASTRUCTURE_ERROR
    val_mixed_1 = {
        "quality_gate": "FAIL",
        "ruff": {"status": "PASS", "output": "Passed cleanly", "result": ToolResult(tool="ruff", command=["ruff"], cwd="/tmp", exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS).model_dump()},
        "pytest": {"status": "ERROR", "output": "Pytest missing", "result": ToolResult(tool="pytest", command=["pytest"], cwd="/tmp", exit_code=None, stdout="", stderr="", execution_error="FileNotFoundError", duration_ms=1.0, status=ToolStatus.INFRASTRUCTURE_ERROR).model_dump()},
    }
    res_mixed_1 = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_mixed_1)
    assert "Ruff Linter Status: PASS" in res_mixed_1["output"]
    assert "Pytest Execution Status: INFRASTRUCTURE_ERROR" in res_mixed_1["output"]

    # 16. Ruff LINT_FAILURE + Pytest PASS
    val_mixed_2 = {
        "quality_gate": "FAIL",
        "ruff": {"status": "FAIL", "output": "F821 error", "result": ToolResult(tool="ruff", command=["ruff"], cwd="/tmp", exit_code=1, stdout="F821 error", stderr="", duration_ms=10.0, status=ToolStatus.LINT_FAILURE).model_dump()},
        "pytest": {"status": "PASS", "output": "1 passed", "result": ToolResult(tool="pytest", command=["pytest"], cwd="/tmp", exit_code=0, stdout="1 passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS).model_dump()},
    }
    res_mixed_2 = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_mixed_2)
    assert "Ruff Linter Status: LINT_FAILURE" in res_mixed_2["output"]
    assert "Pytest Execution Status: PASS" in res_mixed_2["output"]


@pytest.mark.asyncio
async def test_17_missing_evidence_marked_unavailable(mock_ollama_client):
    """17. Missing evidence → Reviewer explicitly identifies evidence as UNAVAILABLE."""
    reviewer = ReviewerAgent(mock_ollama_client)
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=None)

    assert "Ruff Linter Status: UNAVAILABLE" in res["output"]
    assert "Pytest Execution Status: UNAVAILABLE" in res["output"]
    assert "CodeContract Status: UNAVAILABLE" in res["output"]


@pytest.mark.asyncio
async def test_18_19_20_facts_and_inferences_distinguishable(mock_ollama_client):
    """
    18. Facts and inferences are distinguishable.
    19. Reviewer does not claim tests were run when no test execution evidence exists.
    20. Reviewer does not claim Ruff found violations when Ruff never successfully executed.
    """
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "ruff": {"status": "ERROR", "output": "Tool execution failed", "result": ToolResult(tool="ruff", command=["ruff"], cwd="/tmp", exit_code=None, stdout="", stderr="", execution_error="TimeoutExpired", duration_ms=3000.0, status=ToolStatus.INFRASTRUCTURE_ERROR).model_dump()},
    }
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Code quality or defects cannot be evaluated from this tool" in res["output"]
    assert "Ruff found" not in res["output"]
    assert "tests failed" not in res["output"]
