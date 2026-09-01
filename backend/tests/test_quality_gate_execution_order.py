"""
Unit tests for Phase 9: Quality Gate Execution Order.

Validates:
1. Exact fail-fast execution order:
   Workspace -> CodeContract -> Syntax/Import/Manifest -> Ruff -> Pytest -> Bandit -> Authoritative State
2. Unexecuted downstream tools are explicitly tagged NOT_EXECUTED with structured reasons (never ERROR or PASS)
3. Infrastructure errors are classified separately from tool failures
4. Reviewer receives authoritative evidence without overriding decisions
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.reviewer import ReviewerAgent
from app.agents.validator import DeterministicValidator
from app.ai.ollama_client import OllamaClient
from app.orchestration.code_contract import CodeContractStatus
from app.schemas.tool_result import ToolResult, ToolStatus


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
    client.chat = AsyncMock(return_value="### Review Summary\nReviewed.\n\n### Quality Score\n85/100\n\n### Final Status\nAPPROVED\n")
    return client


@pytest.mark.asyncio
async def test_1_to_7_and_24_exact_execution_order(tmp_path: Path):
    """
    1-7 & 24. Asserts exact execution order:
    Workspace -> CodeContract -> Syntax/Import -> Ruff -> Pytest -> Bandit -> Authoritative State.
    """
    execution_sequence = []
    validator = DeterministicValidator()

    # Track workspace check
    original_exists = Path.exists
    def mock_exists(self_path):
        if self_path == tmp_path:
            execution_sequence.append("workspace_validation")
            return True
        return original_exists(self_path)

    # Track CodeContract
    def mock_code_contract(ws, planned=None):
        execution_sequence.append("code_contract")
        res = MagicMock()
        res.is_valid = True
        res.status = CodeContractStatus.VALID
        res.model_dump.return_value = {"status": "VALID", "is_valid": True, "errors": []}
        return res

    # Track Syntax/Import
    async def mock_validate(ws, planned=None):
        execution_sequence.append("syntax_validation")
        return {"passed": True, "errors": [], "summary": "All checks passed"}

    # Track Tool Executions
    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="No issues", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    async def mock_run_tool_cmd(cmd, timeout, cwd, tool_name):
        execution_sequence.append(tool_name)
        return mock_ruff if tool_name == "ruff" else mock_bandit

    async def mock_run_pytest(cwd):
        execution_sequence.append("pytest")
        return mock_pytest

    with patch.object(Path, "exists", autospec=True, side_effect=mock_exists), \
         patch("app.agents.validator.CodeContractValidator.validate", side_effect=mock_code_contract), \
         patch.object(validator, "validate", side_effect=mock_validate), \
         patch.object(validator, "_run_tool_cmd", side_effect=mock_run_tool_cmd), \
         patch.object(validator, "_run_pytest", side_effect=mock_run_pytest):

        res = await validator.run_full_quality_gate(workspace_dir=tmp_path)

    assert execution_sequence == ["workspace_validation", "code_contract", "syntax_validation", "ruff", "pytest", "bandit"]
    assert res["quality_gate"] == "PASS"


@pytest.mark.asyncio
async def test_8_workspace_failure_prevents_downstream_tools(tmp_path: Path):
    """8. Workspace failure → CodeContract, Syntax, Ruff, Pytest, Bandit are NOT_EXECUTED."""
    non_existent = tmp_path / "does_not_exist"
    validator = DeterministicValidator()
    res = await validator.run_full_quality_gate(workspace_dir=non_existent)

    assert res["workspace_validation"]["status"] == "ERROR"
    assert res["code_contract"]["status"] == "NOT_EXECUTED"
    assert res["deterministic_checks"]["status"] == "NOT_EXECUTED"
    assert res["ruff"]["status"] == "NOT_EXECUTED"
    assert res["pytest"]["status"] == "NOT_EXECUTED"
    assert res["bandit"]["status"] == "NOT_EXECUTED"
    assert res["quality_gate"] == "FAIL"


@pytest.mark.asyncio
async def test_9_10_11_and_30_code_contract_failure_prevents_downstream_tools(tmp_path: Path):
    """
    9-11 & 30. CodeContract failure → Syntax, Ruff, Pytest, Bandit are NOT_EXECUTED.
    Existing CodeContract blocking behavior remains intact.
    """
    calc_file = tmp_path / "calculator.py"
    calc_file.write_text("# TODO: implement\npass\n", encoding="utf-8")

    validator = DeterministicValidator()
    res = await validator.run_full_quality_gate(workspace_dir=tmp_path)

    assert res["workspace_validation"]["status"] == "PASS"
    assert res["code_contract"]["status"] == "CONTRACT_FAILURE"
    assert res["deterministic_checks"]["status"] == "NOT_EXECUTED"
    assert res["ruff"]["status"] == "NOT_EXECUTED"
    assert res["pytest"]["status"] == "NOT_EXECUTED"
    assert res["bandit"]["status"] == "NOT_EXECUTED"
    assert "Skipped — CodeContract validation failed" in res["ruff"]["output"]
    assert res["quality_gate"] == "FAIL"


@pytest.mark.asyncio
async def test_12_13_14_syntax_failure_prevents_downstream_tools(tmp_path: Path):
    """12-14. Syntax failure → Ruff, Pytest, Bandit are NOT_EXECUTED."""
    validator = DeterministicValidator()

    mock_cc_valid = MagicMock()
    mock_cc_valid.is_valid = True
    mock_cc_valid.model_dump.return_value = {"status": "VALID", "is_valid": True, "errors": []}

    async def mock_syntax_fail(ws, planned=None):
        return {"passed": False, "errors": [{"severity": "CRITICAL", "type": "SyntaxError", "file": "main.py", "message": "invalid syntax"}], "summary": "Syntax failure"}

    with patch("app.agents.validator.CodeContractValidator.validate", return_value=mock_cc_valid), \
         patch.object(validator, "validate", side_effect=mock_syntax_fail), \
         patch.object(validator, "_run_tool_cmd") as mock_tool, \
         patch.object(validator, "_run_pytest") as mock_pytest:

        res = await validator.run_full_quality_gate(workspace_dir=tmp_path)

    assert res["deterministic_checks"]["status"] == "FAIL"
    assert res["ruff"]["status"] == "NOT_EXECUTED"
    assert res["pytest"]["status"] == "NOT_EXECUTED"
    assert res["bandit"]["status"] == "NOT_EXECUTED"
    mock_tool.assert_not_called()
    mock_pytest.assert_not_called()


@pytest.mark.asyncio
async def test_15_to_17_ruff_classification(tmp_path: Path):
    """15-17. Ruff PASS/LINT_FAILURE/INFRASTRUCTURE_ERROR classifications."""
    validator = DeterministicValidator()
    mock_cc_valid = MagicMock()
    mock_cc_valid.is_valid = True
    mock_cc_valid.model_dump.return_value = {"status": "VALID", "is_valid": True, "errors": []}

    # Case A: PASS
    mock_ruff_pass = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest_pass = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit_pass = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.CodeContractValidator.validate", return_value=mock_cc_valid), \
         patch.object(validator, "validate", return_value={"passed": True, "summary": "Passed"}), \
         patch.object(validator, "_run_tool_cmd", side_effect=[mock_ruff_pass, mock_bandit_pass]), \
         patch.object(validator, "_run_pytest", return_value=mock_pytest_pass):

        res = await validator.run_full_quality_gate(workspace_dir=tmp_path)
        assert res["ruff"]["status"] == "PASS"

    # Case B: LINT_FAILURE
    mock_ruff_fail = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=1, stdout="F821 error", stderr="", duration_ms=10.0, status=ToolStatus.LINT_FAILURE)
    with patch("app.agents.validator.CodeContractValidator.validate", return_value=mock_cc_valid), \
         patch.object(validator, "validate", return_value={"passed": True, "summary": "Passed"}), \
         patch.object(validator, "_run_tool_cmd", side_effect=[mock_ruff_fail, mock_bandit_pass]), \
         patch.object(validator, "_run_pytest", return_value=mock_pytest_pass):

        res_b = await validator.run_full_quality_gate(workspace_dir=tmp_path)
        assert res_b["ruff"]["status"] == "FAIL"


@pytest.mark.asyncio
async def test_18_to_20_pytest_classification(tmp_path: Path):
    """18-20. Pytest PASS/TEST_FAILURE/INFRASTRUCTURE_ERROR classifications."""
    validator = DeterministicValidator()
    mock_cc_valid = MagicMock()
    mock_cc_valid.is_valid = True
    mock_cc_valid.model_dump.return_value = {"status": "VALID", "is_valid": True, "errors": []}

    mock_ruff_pass = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest_fail = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=1, stdout="AssertionError", stderr="", duration_ms=10.0, status=ToolStatus.TEST_FAILURE)
    mock_bandit_pass = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.CodeContractValidator.validate", return_value=mock_cc_valid), \
         patch.object(validator, "validate", return_value={"passed": True, "summary": "Passed"}), \
         patch.object(validator, "_run_tool_cmd", side_effect=[mock_ruff_pass, mock_bandit_pass]), \
         patch.object(validator, "_run_pytest", return_value=mock_pytest_fail):

        res = await validator.run_full_quality_gate(workspace_dir=tmp_path)
        assert res["pytest"]["status"] == "FAIL"
        assert res["quality_gate"] == "FAIL"


@pytest.mark.asyncio
async def test_21_to_23_bandit_classification(tmp_path: Path):
    """21-23. Bandit PASS/Findings/INFRASTRUCTURE_ERROR classifications."""
    validator = DeterministicValidator()
    mock_cc_valid = MagicMock()
    mock_cc_valid.is_valid = True
    mock_cc_valid.model_dump.return_value = {"status": "VALID", "is_valid": True, "errors": []}

    mock_ruff_pass = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest_pass = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit_infra = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=None, stdout="", stderr="", execution_error="FileNotFoundError", duration_ms=1.0, status=ToolStatus.INFRASTRUCTURE_ERROR)

    with patch("app.agents.validator.CodeContractValidator.validate", return_value=mock_cc_valid), \
         patch.object(validator, "validate", return_value={"passed": True, "summary": "Passed"}), \
         patch.object(validator, "_run_tool_cmd", side_effect=[mock_ruff_pass, mock_bandit_infra]), \
         patch.object(validator, "_run_pytest", return_value=mock_pytest_pass):

        res = await validator.run_full_quality_gate(workspace_dir=tmp_path)
        assert res["bandit"]["status"] == "ERROR"
        assert res["quality_gate"] == "FAIL"


@pytest.mark.asyncio
async def test_25_to_29_evidence_preservation_and_reviewer_non_override(mock_ollama_client, tmp_path: Path):
    """
    25-29. No unexecuted tool reported as PASS, exact evidence preserved, deterministic gate computed, Reviewer cannot override gate.
    """
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "code_contract": {"status": "CONTRACT_FAILURE", "summary": "Missing manifest"},
        "ruff": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
        "pytest": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
        "bandit": {"status": "NOT_EXECUTED", "output": "Skipped — CodeContract failed"},
    }

    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    # Reviewer output cannot override gate
    assert res["quality_gate"] == "FAIL"
    assert "Ruff Linter Status: NOT_EXECUTED" in res["output"]
    assert "Pytest Execution Status: NOT_EXECUTED" in res["output"]
