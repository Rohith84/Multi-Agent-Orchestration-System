"""
Unit tests for the Internal Deterministic Quality Gate (DeterministicValidator).
Validates:
  1. Intentionally broken Python syntax detection & repair
  2. Missing file manifest detection & repair
"""

from __future__ import annotations

import pytest
from pathlib import Path
from app.agents.validator import DeterministicValidator


@pytest.mark.asyncio
async def test_quality_gate_syntax_error_detection_and_repair(tmp_path: Path):
    """
    Test 1: Intentionally broken code syntax error detection & repair flow.
    1. Create a file with a SyntaxError (unclosed parenthesis).
    2. Verify DeterministicValidator catches SyntaxError with line number and file path.
    3. Repair the file with valid Python syntax.
    4. Verify DeterministicValidator returns passed=True.
    """
    validator = DeterministicValidator()
    workspace_dir = tmp_path / "sandbox"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    # 1. Create file with SyntaxError
    broken_file = workspace_dir / "broken_tasks.py"
    broken_file.write_text(
        "def create_task(name: str):\n"
        "    return dict(\n"
        "        name=name,\n"
        "        status='pending'\n"  # missing closing parenthesis ')'
        "\n"
        "def get_tasks():\n"
        "    return []\n",
        encoding="utf-8",
    )

    # 2. Run validator — expect failure
    result = await validator.validate(workspace_dir)
    assert result["passed"] is False, "Validator should fail on SyntaxError"
    assert len(result["errors"]) >= 1

    syntax_err = result["errors"][0]
    assert syntax_err["type"] == "SyntaxError"
    assert "broken_tasks.py" in syntax_err["file"]
    assert syntax_err["line"] is not None
    assert syntax_err["severity"] == "CRITICAL"

    # 3. Simulate Coder repair — write syntactically correct code
    broken_file.write_text(
        "def create_task(name: str):\n"
        "    return dict(\n"
        "        name=name,\n"
        "        status='pending'\n"
        "    )\n\n"
        "def get_tasks():\n"
        "    return []\n",
        encoding="utf-8",
    )

    # 4. Re-run validator — expect pass
    repaired_result = await validator.validate(workspace_dir)
    assert repaired_result["passed"] is True, "Validator should pass after syntax fix"
    assert len(repaired_result["errors"]) == 0


@pytest.mark.asyncio
async def test_quality_gate_missing_file_manifest_detection_and_repair(tmp_path: Path):
    """
    Test 2: Missing file detection & repair flow based on Planner's file manifest.
    1. Define planned files: models.py, schemas.py, routes.py.
    2. Coder generates models.py and routes.py, but omits schemas.py.
    3. Verify DeterministicValidator detects MissingFile for schemas.py.
    4. Coder generates schemas.py.
    5. Verify DeterministicValidator returns passed=True.
    """
    validator = DeterministicValidator()
    workspace_dir = tmp_path / "sandbox"
    workspace_dir.mkdir(parents=True, exist_ok=True)

    planned_files = ["models.py", "schemas.py", "routes.py"]

    # 1. Generate only models.py and routes.py (omitting schemas.py)
    (workspace_dir / "models.py").write_text("class Task: pass\n", encoding="utf-8")
    (workspace_dir / "routes.py").write_text("def get_routes(): pass\n", encoding="utf-8")

    # 2. Run validator with file manifest check — expect failure
    result = await validator.validate(workspace_dir, planned_files=planned_files)
    assert result["passed"] is False, "Validator should fail when planned file is missing"

    missing_errs = [e for e in result["errors"] if e["type"] == "MissingFile"]
    assert len(missing_errs) == 1
    assert missing_errs[0]["file"] == "schemas.py"
    assert "schemas.py" in missing_errs[0]["message"]

    # 3. Simulate Coder repair — generate missing schemas.py
    (workspace_dir / "schemas.py").write_text("class TaskSchema: pass\n", encoding="utf-8")

    # 4. Re-run validator — expect pass
    repaired_result = await validator.validate(workspace_dir, planned_files=planned_files)
    assert repaired_result["passed"] is True, "Validator should pass after missing file is created"
    assert len(repaired_result["errors"]) == 0
