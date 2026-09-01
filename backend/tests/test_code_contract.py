"""
Unit tests for Phase 5: Deterministic Code Contract Validator.

Validates that CodeContractValidator detects empty files, syntax errors, incomplete function stubs,
placeholder comments, and missing manifest files while preserving legitimate abstract methods and ellipsis usage.
Also verifies read-only behavior, path traversal protection, and Quality Gate execution blocking.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from app.agents.validator import DeterministicValidator
from app.orchestration.code_contract import (
    CodeContractResult,
    CodeContractStatus,
    CodeContractValidator,
)


def test_1_valid_python_implementation(tmp_path: Path):
    """1. Valid Python implementation → VALID."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "calculator.py").write_text(
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n\n"
        "def subtract(a: int, b: int) -> int:\n"
        "    return a - b\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is True
    assert res.status == CodeContractStatus.VALID
    assert len(res.errors) == 0


def test_2_empty_python_file(tmp_path: Path):
    """2. Empty Python file → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "empty.py").write_bytes(b"")
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert any(e.rule == "EMPTY_FILE" for e in res.errors)


def test_3_whitespace_only_file(tmp_path: Path):
    """3. Whitespace-only file → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "whitespace.py").write_text("   \n\t  \n  \n", encoding="utf-8")
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert any(e.rule in ("COMMENT_OR_WHITESPACE_ONLY", "EMPTY_FILE") for e in res.errors)


def test_4_comment_only_file(tmp_path: Path):
    """4. Comment-only file → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "comments.py").write_text(
        "# This is a module header\n"
        "# Another comment line\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert any(e.rule == "COMMENT_OR_WHITESPACE_ONLY" for e in res.errors)


def test_5_syntax_error(tmp_path: Path):
    """5. Syntax error → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "broken.py").write_text(
        "def broken_function(\n"
        "    x = 1 +\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert any(e.rule == "SYNTAX_ERROR" for e in res.errors)


def test_6_function_containing_only_pass(tmp_path: Path):
    """6. Function containing only pass → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "stub.py").write_text(
        "def calculate():\n"
        "    pass\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert any(e.rule == "CONCRETE_FUNCTION_PASS" for e in res.errors)


def test_7_function_raising_not_implemented_error(tmp_path: Path):
    """7. Function raising NotImplementedError → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "stub.py").write_text(
        "def calculate():\n"
        "    raise NotImplementedError('Not ready yet')\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert any(e.rule == "CONCRETE_FUNCTION_NOT_IMPLEMENTED" for e in res.errors)


def test_8_placeholder_implementation_here(tmp_path: Path):
    """8. '# implementation here' → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text(
        "def main():\n"
        "    # implementation here\n"
        "    return 0\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert any(e.rule == "PLACEHOLDER_COMMENT" for e in res.errors)


def test_9_placeholder_todo_implement(tmp_path: Path):
    """9. '# TODO: implement' → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text(
        "def process():\n"
        "    # TODO: implement\n"
        "    return True\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert any(e.rule == "PLACEHOLDER_COMMENT" for e in res.errors)


def test_10_placeholder_add_more_here(tmp_path: Path):
    """10. '# add more here' → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text(
        "# add more here\n"
        "x = 10\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert any(e.rule == "PLACEHOLDER_COMMENT" for e in res.errors)


def test_11_placeholder_rest_of_code(tmp_path: Path):
    """11. '# ... rest of code' → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text(
        "# ... rest of code\n"
        "def foo(): return 1\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert any(e.rule == "PLACEHOLDER_COMMENT" for e in res.errors)


def test_12_missing_manifest_file(tmp_path: Path):
    """12. Missing manifest file → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")
    planned = ["main.py", "missing_schema.py"]

    res = CodeContractValidator.validate(workspace, planned_files=planned)
    assert res.is_valid is False
    assert any(e.rule == "MISSING_MANIFEST_FILE" and e.file == "missing_schema.py" for e in res.errors)


def test_13_valid_abstract_method_with_pass(tmp_path: Path):
    """13. Valid abstract method with pass → VALID."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "base.py").write_text(
        "from abc import ABC, abstractmethod\n\n"
        "class BaseWorker(ABC):\n"
        "    @abstractmethod\n"
        "    def execute(self) -> None:\n"
        "        pass\n\n"
        "    def run((self) -> None:\n"
        "        self.execute()\n",
        encoding="utf-8",
    )
    # Fix syntax in run method
    (workspace / "base.py").write_text(
        "from abc import ABC, abstractmethod\n\n"
        "class BaseWorker(ABC):\n"
        "    @abstractmethod\n"
        "    def execute(self) -> None:\n"
        "        pass\n\n"
        "    def run(self) -> None:\n"
        "        self.execute()\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is True
    assert res.status == CodeContractStatus.VALID


def test_14_legitimate_ellipsis_usage(tmp_path: Path):
    """14. Legitimate ellipsis usage (e.g. typing Protocol or tuple type annotation) → VALID."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "types.py").write_text(
        "from typing import Protocol, Tuple\n\n"
        "class WorkerProtocol(Protocol):\n"
        "    def execute(self) -> None:\n"
        "        ...\n\n"
        "DataTuple = Tuple[int, ...]\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is True
    assert res.status == CodeContractStatus.VALID


def test_15_multiple_valid_python_files(tmp_path: Path):
    """15. Multiple valid Python files → VALID."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "models.py").write_text("class User:\n    def __init__(self, name: str):\n        self.name = name\n", encoding="utf-8")
    (workspace / "utils.py").write_text("def format_name(name: str) -> str:\n    return name.strip().title()\n", encoding="utf-8")

    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is True


def test_16_one_invalid_file_among_multiple_valid_files(tmp_path: Path):
    """16. One invalid file among multiple valid files → CONTRACT_FAILURE."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "models.py").write_text("class User: pass\n", encoding="utf-8")
    (workspace / "broken.py").write_text("def foo():\n    # TODO: implement\n    return 1\n", encoding="utf-8")

    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert len(res.errors) >= 1
    assert any(e.file == "broken.py" for e in res.errors)


def test_17_non_python_dependency_file_with_valid_content(tmp_path: Path):
    """17. Non-Python dependency file with valid content → VALID."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "requirements.txt").write_text("fastapi==0.110.0\npydantic>=2.0\n", encoding="utf-8")
    (workspace / "main.py").write_text("def run(): return True\n", encoding="utf-8")

    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is True


def test_18_empty_required_dependency_file(tmp_path: Path):
    """18. Empty required dependency file → CONTRACT_FAILURE if required by manifest."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("x = 1\n", encoding="utf-8")
    (workspace / "requirements.txt").write_bytes(b"")

    res = CodeContractValidator.validate(workspace, planned_files=["main.py", "requirements.txt"])
    assert res.is_valid is False
    assert any(e.file == "requirements.txt" and e.rule == "EMPTY_FILE" for e in res.errors)


def test_19_failure_reports_exact_offending_file(tmp_path: Path):
    """19. Verify failure reports the exact offending file."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    sub_dir = workspace / "sub"
    sub_dir.mkdir()
    (sub_dir / "target_file.py").write_text("def bad():\n    pass\n", encoding="utf-8")

    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    assert any("target_file.py" in e.file for e in res.errors)


def test_20_useful_line_number_reported(tmp_path: Path):
    """20. Verify useful line number is reported when available."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "lines.py").write_text(
        "x = 1\n"
        "y = 2\n"
        "def stub():\n"
        "    pass\n",
        encoding="utf-8",
    )
    res = CodeContractValidator.validate(workspace)
    assert res.is_valid is False
    err = next(e for e in res.errors if e.rule == "CONCRETE_FUNCTION_PASS")
    assert err.line == 3


def test_21_validator_does_not_modify_files(tmp_path: Path):
    """21. Verify validator does not modify files (read-only)."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    target_file = workspace / "test_mod.py"
    original_content = "def calculate():\n    pass\n"
    target_file.write_text(original_content, encoding="utf-8")

    mtime_before = os.path.getmtime(target_file)
    res = CodeContractValidator.validate(workspace)
    mtime_after = os.path.getmtime(target_file)

    assert res.is_valid is False
    assert target_file.read_text(encoding="utf-8") == original_content
    assert mtime_before == mtime_after


def test_22_path_traversal_protection(tmp_path: Path):
    """22. Verify files outside the workspace cannot be inspected through path traversal."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_file = tmp_path / "outside.py"
    outside_file.write_text("secret = 123\n", encoding="utf-8")

    # Attempt path traversal via planned_files manifest
    planned = ["../outside.py"]
    res = CodeContractValidator.validate(workspace, planned_files=planned)

    assert res.is_valid is False
    assert any(e.rule == "PATH_TRAVERSAL_DENIED" or e.rule == "MISSING_MANIFEST_FILE" for e in res.errors)


@pytest.mark.asyncio
async def test_23_quality_gate_blocked_on_code_contract_failure(tmp_path: Path):
    """
    23. Quality Gate boundary test:
    Verify that if CodeContract fails, Quality Gate execution returns FAIL immediately
    and NEITHER Ruff nor Pytest is invoked.
    """
    validator = DeterministicValidator()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "main.py").write_text("def incomplete():\n    pass\n", encoding="utf-8")

    with patch.object(validator, "_run_tool_cmd", new_callable=AsyncMock) as mock_tool, \
         patch.object(validator, "_run_pytest", new_callable=AsyncMock) as mock_pytest:

        res = await validator.run_full_quality_gate(workspace)

        assert res["quality_gate"] == "FAIL"
        assert res["test_passed"] is False
        assert res["ruff"]["status"] == "ERROR"
        assert "Skipped — CodeContract validation failed" in res["ruff"]["output"]
        assert res["pytest"]["status"] == "ERROR"
        assert "Skipped — CodeContract validation failed" in res["pytest"]["output"]

        # CRITICAL ASSERTION: Ruff and Pytest execution methods were NOT invoked
        mock_tool.assert_not_called()
        mock_pytest.assert_not_called()
