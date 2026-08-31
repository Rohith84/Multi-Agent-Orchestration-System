"""
Pipeline Separation Tests — Comprehensive validation of the refactored validation/evaluation pipeline.

Tests verify:
  1. Quality Gate executes all deterministic checks (Ruff, Pytest, Bandit, syntax/imports/manifest)
  2. Structured validation_results are produced and stored
  3. Reviewer does NOT rerun deterministic validation
  4. Tester focuses on test generation and coverage analysis
  5. Missing evidence fails closed (never defaults to PASS)
  6. Fail-open patterns eliminated throughout the pipeline
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from app.agents.validator import DeterministicValidator
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.ai.ollama_client import OllamaClient


# ─── DeterministicValidator Quality Gate Tests ─────────────────────────

@pytest.mark.asyncio
async def test_quality_gate_ruff_fail_forces_gate_fail(tmp_path: Path):
    """Ruff FAIL → Quality Gate FAIL."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = [
            "main.py:1:1: F821 Undefined name `foo`",   # Ruff
            "No issues identified.",                      # Bandit
        ]
        mock_pytest.return_value = "1 passed in 0.5s"

        result = await validator.run_full_quality_gate(workspace)

    assert result["ruff"]["status"] == "FAIL"
    assert result["quality_gate"] == "FAIL"
    assert result["test_passed"] is False


@pytest.mark.asyncio
async def test_quality_gate_pytest_fail_forces_gate_fail(tmp_path: Path):
    """Pytest FAIL → Quality Gate FAIL."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = [
            "Passed cleanly.",          # Ruff
            "No issues identified.",     # Bandit
        ]
        mock_pytest.return_value = "FAILED test_main.py::test_foo - AssertionError"

        result = await validator.run_full_quality_gate(workspace)

    assert result["pytest"]["status"] == "FAIL"
    assert result["quality_gate"] == "FAIL"
    assert result["test_passed"] is False


@pytest.mark.asyncio
async def test_quality_gate_pytest_collection_error_forces_fail(tmp_path: Path):
    """Pytest collection error (collected 0 items) → Quality Gate FAIL."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = [
            "Passed cleanly.",          # Ruff
            "No issues identified.",     # Bandit
        ]
        mock_pytest.return_value = "collected 0 items / 1 error\nSyntaxError in test_main.py"

        result = await validator.run_full_quality_gate(workspace)

    assert result["pytest"]["status"] == "FAIL"
    assert result["quality_gate"] == "FAIL"


@pytest.mark.asyncio
async def test_quality_gate_bandit_high_forces_fail(tmp_path: Path):
    """High/Critical Bandit finding → Quality Gate FAIL."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = [
            "Passed cleanly.",                              # Ruff
            ">> Issue: [B602] Severity: High Confidence: High",  # Bandit
        ]
        mock_pytest.return_value = "1 passed in 0.5s"

        result = await validator.run_full_quality_gate(workspace)

    assert result["bandit"]["status"] == "FAIL"
    assert result["quality_gate"] == "FAIL"


@pytest.mark.asyncio
async def test_quality_gate_bandit_medium_gives_warning(tmp_path: Path):
    """Medium Bandit finding → PASS_WITH_WARNINGS (not FAIL)."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = [
            "Passed cleanly.",                                # Ruff
            ">> Issue: [B108] Severity: Medium Confidence: High",  # Bandit
        ]
        mock_pytest.return_value = "1 passed in 0.5s"

        result = await validator.run_full_quality_gate(workspace)

    assert result["bandit"]["status"] == "WARNING"
    assert result["quality_gate"] == "PASS_WITH_WARNINGS"
    assert result["test_passed"] is True  # PASS_WITH_WARNINGS still passes


@pytest.mark.asyncio
async def test_quality_gate_all_clean_passes(tmp_path: Path):
    """All checks clean → Quality Gate PASS."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = [
            "Passed cleanly.",          # Ruff
            "No issues identified.",     # Bandit
        ]
        mock_pytest.return_value = "5 passed in 1.2s"

        result = await validator.run_full_quality_gate(workspace)

    assert result["quality_gate"] == "PASS"
    assert result["test_passed"] is True
    assert result["ruff"]["status"] == "PASS"
    assert result["pytest"]["status"] == "PASS"
    assert result["bandit"]["status"] == "PASS"


@pytest.mark.asyncio
async def test_quality_gate_missing_workspace_fails(tmp_path: Path):
    """Missing workspace directory → Quality Gate FAIL (fail-closed)."""
    validator = DeterministicValidator()
    nonexistent = tmp_path / "does_not_exist"

    result = await validator.run_full_quality_gate(nonexistent)

    assert result["quality_gate"] == "FAIL"
    assert result["test_passed"] is False
    assert result["deterministic_checks"]["status"] == "ERROR"


@pytest.mark.asyncio
async def test_quality_gate_no_test_files(tmp_path: Path):
    """No test files in workspace → pytest returns error message."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool:
        mock_tool.side_effect = [
            "Passed cleanly.",          # Ruff
            "No issues identified.",     # Bandit
        ]
        # _run_pytest is NOT mocked — will actually check for test files

        result = await validator.run_full_quality_gate(workspace)

    # No test files means pytest returns error-like output
    assert result["pytest"]["output"] == "No test files found in workspace."


@pytest.mark.asyncio
async def test_quality_gate_produces_structured_results(tmp_path: Path):
    """Quality Gate produces all required structured fields."""
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:
        mock_tool.side_effect = ["Passed cleanly.", "No issues identified."]
        mock_pytest.return_value = "1 passed in 0.2s"

        result = await validator.run_full_quality_gate(workspace)

    # Verify all required fields exist
    required_keys = ["deterministic_checks", "ruff", "pytest", "bandit", "quality_gate", "test_passed"]
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"

    # Verify each tool result has status and output
    for tool in ["deterministic_checks", "ruff", "pytest", "bandit"]:
        assert "status" in result[tool], f"Missing 'status' in {tool}"
        assert "output" in result[tool], f"Missing 'output' in {tool}"


# ─── Reviewer Agent Pipeline Tests ────────────────────────────────────

@pytest.mark.asyncio
async def test_reviewer_does_not_run_linters():
    """Reviewer MUST NOT have _run_linter_cmd method (removed in refactor)."""
    client = OllamaClient()
    agent = ReviewerAgent(client)
    assert not hasattr(agent, "_run_linter_cmd"), "Reviewer must not have _run_linter_cmd — linting moved to Quality Gate"


@pytest.mark.asyncio
async def test_reviewer_pass_cannot_override_gate_fail():
    """Reviewer returning PASS text cannot override Quality Gate FAIL."""
    client = OllamaClient()
    agent = ReviewerAgent(client)

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = (
            "Quality Score: 95/100\n"
            "Correctness: PASS\n"
            "Final Status: APPROVED"
        )

        validation_results = {
            "deterministic_checks": {"status": "PASS", "output": "OK"},
            "ruff": {"status": "FAIL", "output": "F821 error"},
            "pytest": {"status": "PASS", "output": "1 passed"},
            "bandit": {"status": "PASS", "output": "OK"},
            "quality_gate": "FAIL",
            "test_passed": False,
        }

        result = await agent.execute(
            user_request="test",
            execution_plan="plan",
            generated_code="code",
            test_results="",
            validation_results=validation_results,
        )

    assert result["quality_gate"] == "FAIL", "Reviewer PASS text cannot override Quality Gate FAIL"
    assert result["overall_score"] <= 40.0


@pytest.mark.asyncio
async def test_reviewer_pass_with_warnings():
    """Quality Gate PASS_WITH_WARNINGS flows through to reviewer output."""
    client = OllamaClient()
    agent = ReviewerAgent(client)

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "Quality Score: 78/100\nFinal Status: APPROVED_WITH_WARNINGS"

        validation_results = {
            "deterministic_checks": {"status": "PASS", "output": "OK"},
            "ruff": {"status": "PASS", "output": "OK"},
            "pytest": {"status": "PASS", "output": "3 passed"},
            "bandit": {"status": "WARNING", "output": "Severity: Medium"},
            "quality_gate": "PASS_WITH_WARNINGS",
            "test_passed": True,
        }

        result = await agent.execute(
            user_request="test",
            execution_plan="plan",
            generated_code="code",
            test_results="3 passed",
            validation_results=validation_results,
        )

    assert result["quality_gate"] == "PASS_WITH_WARNINGS"
    assert "APPROVED_WITH_WARNINGS" in result["output"]


# ─── Tester Agent Pipeline Tests ──────────────────────────────────────

@pytest.mark.asyncio
async def test_tester_does_not_run_pytest():
    """Tester MUST NOT have _run_pytest_subprocess method (removed in refactor)."""
    client = OllamaClient()
    agent = TesterAgent(client)
    assert not hasattr(agent, "_run_pytest_subprocess"), "Tester must not have _run_pytest_subprocess — execution moved to Quality Gate"


@pytest.mark.asyncio
async def test_tester_returns_analysis_not_execution():
    """Tester returns tester_analysis string, not execution results."""
    client = OllamaClient()
    agent = TesterAgent(client)

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = (
            "```python filepath=\"test_suite.py\"\n"
            "import pytest\n"
            "def test_example():\n"
            "    assert True\n"
            "```\n\n"
            "Coverage Assessment: ADEQUATE\n"
        )

        result = await agent.execute(
            generated_code="def task(): pass",
            execution_plan="Plan",
        )

    assert "tester_analysis" in result, "Tester must return tester_analysis"
    assert "output" in result
    assert "passed" not in result, "Tester must not return 'passed' — Quality Gate determines pass/fail"
    assert "bug_report" not in result, "Tester must not return bug_report — Quality Gate determines issues"


# ─── Classification Helper Tests ──────────────────────────────────────

def test_classify_ruff_status_pass():
    assert DeterministicValidator._classify_ruff_status("Passed cleanly.") == "PASS"
    assert DeterministicValidator._classify_ruff_status("") == "PASS"


def test_classify_ruff_status_fail():
    assert DeterministicValidator._classify_ruff_status("main.py:1:1: F821 Undefined name") == "FAIL"
    assert DeterministicValidator._classify_ruff_status("main.py:1:1: E999 SyntaxError") == "FAIL"


def test_classify_tool_execution_failure_as_error():
    output = "Tool execution error: NotImplementedError: no additional detail"
    assert DeterministicValidator._classify_ruff_status(output) == "ERROR"
    assert DeterministicValidator._classify_pytest_status(output) == "ERROR"
    assert DeterministicValidator._classify_bandit_status(output) == "ERROR"


def test_classify_ruff_status_warning():
    assert DeterministicValidator._classify_ruff_status("main.py:1:1: W292 no newline at end of file") == "WARNING"


def test_classify_pytest_status_pass():
    assert DeterministicValidator._classify_pytest_status("5 passed in 1.2s") == "PASS"


def test_classify_pytest_status_fail():
    assert DeterministicValidator._classify_pytest_status("FAILED test_main.py::test_foo") == "FAIL"
    assert DeterministicValidator._classify_pytest_status("collected 0 items / 1 error") == "FAIL"


def test_classify_pytest_status_missing():
    """Missing pytest output should return ERROR, not PASS."""
    assert DeterministicValidator._classify_pytest_status("") == "ERROR"
    assert DeterministicValidator._classify_pytest_status(None) == "ERROR"


def test_classify_bandit_status_pass():
    assert DeterministicValidator._classify_bandit_status("No issues identified.") == "PASS"


def test_classify_bandit_status_warning():
    assert DeterministicValidator._classify_bandit_status("Severity: Medium") == "WARNING"


def test_classify_bandit_status_fail():
    assert DeterministicValidator._classify_bandit_status("Severity: High") == "FAIL"
    assert DeterministicValidator._classify_bandit_status("Severity: Critical") == "FAIL"
