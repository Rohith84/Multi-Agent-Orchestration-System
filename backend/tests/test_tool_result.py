"""
Unit tests for Phase 4: Structured Tool Execution Result and Diagnostic Classification.

Tests deterministic classification and execution error handling without requiring real CLI binaries.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from app.schemas.tool_result import (
    ToolResult,
    ToolStatus,
    classify_tool_result,
    execute_tool,
)


def test_1_successful_ruff_execution():
    """1. Successful Ruff execution: exit_code=0 → PASS."""
    res = classify_tool_result(
        tool="ruff",
        command=["ruff", "check", "."],
        cwd="/tmp/test",
        exit_code=0,
        stdout="All checks passed!",
        stderr="",
        duration_ms=45.2,
    )
    assert res.status == ToolStatus.PASS
    assert res.exit_code == 0


def test_2_successful_pytest_execution():
    """2. Successful Pytest execution: exit_code=0 → PASS."""
    res = classify_tool_result(
        tool="pytest",
        command=["pytest", "tests/"],
        cwd="/tmp/test",
        exit_code=0,
        stdout="5 passed in 0.23s",
        stderr="",
        duration_ms=230.1,
    )
    assert res.status == ToolStatus.PASS
    assert res.exit_code == 0


def test_3_ruff_lint_failure():
    """3. Ruff lint failure: exit_code=1 → LINT_FAILURE."""
    res = classify_tool_result(
        tool="ruff",
        command=["ruff", "check", "."],
        cwd="/tmp/test",
        exit_code=1,
        stdout="main.py:1:1: F821 Undefined name `x`",
        stderr="",
        duration_ms=50.0,
    )
    assert res.status == ToolStatus.LINT_FAILURE
    assert res.exit_code == 1


def test_4_pytest_assertion_failure():
    """4. Pytest assertion failure: exit_code=1 → TEST_FAILURE."""
    res = classify_tool_result(
        tool="pytest",
        command=["pytest", "tests/"],
        cwd="/tmp/test",
        exit_code=1,
        stdout="FAILED test_main.py::test_foo - AssertionError: assert 1 == 2",
        stderr="",
        duration_ms=120.0,
    )
    assert res.status == ToolStatus.TEST_FAILURE
    assert res.exit_code == 1


def test_5_configuration_failure():
    """5. Configuration failure: exit_code=2 → CONFIG_ERROR."""
    res = classify_tool_result(
        tool="pytest",
        command=["pytest", "--invalid-flag"],
        cwd="/tmp/test",
        exit_code=2,
        stdout="",
        stderr="pytest: error: unrecognized arguments: --invalid-flag",
        duration_ms=15.0,
    )
    assert res.status == ToolStatus.CONFIG_ERROR
    assert res.exit_code == 2


def test_6_missing_executable():
    """6. Missing executable: FileNotFoundError → INFRASTRUCTURE_ERROR."""
    exc = FileNotFoundError(2, "No such file or directory", "ruff")
    res = classify_tool_result(
        tool="ruff",
        command=["ruff", "check", "."],
        cwd="/tmp/test",
        exception=exc,
        duration_ms=5.0,
    )
    assert res.status == ToolStatus.INFRASTRUCTURE_ERROR
    assert res.exit_code is None


def test_7_permission_failure():
    """7. Permission failure: PermissionError → INFRASTRUCTURE_ERROR."""
    exc = PermissionError(13, "Permission denied", "/usr/bin/ruff")
    res = classify_tool_result(
        tool="ruff",
        command=["/usr/bin/ruff"],
        cwd="/tmp/test",
        exception=exc,
        duration_ms=3.0,
    )
    assert res.status == ToolStatus.INFRASTRUCTURE_ERROR
    assert res.exit_code is None


def test_8_timeout_failure():
    """8. Timeout: TimeoutExpired → INFRASTRUCTURE_ERROR."""
    exc = subprocess.TimeoutExpired(cmd=["pytest"], timeout=30.0)
    res = classify_tool_result(
        tool="pytest",
        command=["pytest"],
        cwd="/tmp/test",
        exception=exc,
        duration_ms=30005.0,
    )
    assert res.status == ToolStatus.INFRASTRUCTURE_ERROR
    assert res.exit_code is None


def test_9_infrastructure_errors_have_none_exit_code():
    """9. Verify infrastructure errors have exit_code=None."""
    for exc in [
        FileNotFoundError("missing binary"),
        PermissionError("no access"),
        subprocess.TimeoutExpired(cmd="tool", timeout=10),
        OSError("Cannot launch process"),
    ]:
        res = classify_tool_result(
            tool="tool",
            command=["tool"],
            cwd="/tmp",
            exception=exc,
        )
        assert res.exit_code is None, f"Expected None exit_code for {type(exc).__name__}"
        assert res.status == ToolStatus.INFRASTRUCTURE_ERROR


def test_10_stdout_preserved_exactly():
    """10. Verify stdout is preserved exactly."""
    raw_stdout = "Line 1\n  Line 2\tWith Tabs\nSpecial chars: !@#$%^&*()\n"
    res = classify_tool_result(
        tool="ruff",
        command=["ruff"],
        cwd="/tmp",
        exit_code=0,
        stdout=raw_stdout,
        stderr="some stderr",
    )
    assert res.stdout == raw_stdout


def test_11_stderr_preserved_exactly():
    """11. Verify stderr is preserved exactly."""
    raw_stderr = "WARNING: Config file not found.\nERROR: Failed to connect to server.\n"
    res = classify_tool_result(
        tool="pytest",
        command=["pytest"],
        cwd="/tmp",
        exit_code=1,
        stdout="some stdout",
        stderr=raw_stderr,
    )
    assert res.stderr == raw_stderr


def test_12_execution_error_contains_exception_info():
    """12. Verify execution_error contains the original infrastructure error information."""
    exc = FileNotFoundError("Executable 'custom_tool' was not found on PATH")
    res = classify_tool_result(
        tool="custom_tool",
        command=["custom_tool"],
        cwd="/tmp",
        exception=exc,
    )
    assert res.execution_error is not None
    assert "FileNotFoundError" in res.execution_error
    assert "custom_tool" in res.execution_error


def test_13_command_and_cwd_preserved():
    """13. Verify command and cwd are preserved."""
    cmd = ["pytest", "-v", "--tb=short", "tests/unit/"]
    cwd = "/workspace/my_project"
    res = classify_tool_result(
        tool="pytest",
        command=cmd,
        cwd=cwd,
        exit_code=0,
    )
    assert res.command == cmd
    assert res.cwd == cwd


def test_14_duration_ms_populated():
    """14. Verify duration_ms is populated."""
    res = classify_tool_result(
        tool="ruff",
        command=["ruff"],
        cwd="/tmp",
        exit_code=0,
        duration_ms=123.456,
    )
    assert isinstance(res.duration_ms, float)
    assert res.duration_ms == 123.46


def test_15_ruff_exit_code_1_not_infrastructure_failure():
    """15. Verify Ruff exit code 1 is NOT classified as infrastructure failure."""
    res = classify_tool_result(
        tool="ruff",
        command=["ruff", "check", "."],
        cwd="/tmp",
        exit_code=1,
        stdout="F821 Undefined name",
    )
    assert res.status != ToolStatus.INFRASTRUCTURE_ERROR
    assert res.status == ToolStatus.LINT_FAILURE
    assert res.exit_code == 1


def test_16_pytest_exit_code_1_not_infrastructure_failure():
    """16. Verify Pytest exit code 1 is NOT classified as infrastructure failure."""
    res = classify_tool_result(
        tool="pytest",
        command=["pytest"],
        cwd="/tmp",
        exit_code=1,
        stdout="1 failed, 2 passed",
    )
    assert res.status != ToolStatus.INFRASTRUCTURE_ERROR
    assert res.status == ToolStatus.TEST_FAILURE
    assert res.exit_code == 1


def test_17_unknown_execution_failure_handled_deterministically():
    """17. Verify unknown/nonstandard execution failure is handled deterministically."""
    # Exit code 3 for unknown tool
    res_code3 = classify_tool_result(
        tool="custom_tool",
        command=["custom_tool", "do_thing"],
        cwd="/tmp",
        exit_code=3,
        stdout="",
        stderr="Unknown error code 3",
    )
    assert res_code3.status == ToolStatus.CONFIG_ERROR
    assert res_code3.exit_code == 3

    # Unknown exception without exit code
    res_exc = classify_tool_result(
        tool="unknown_tool",
        command=["unknown_tool"],
        cwd="/tmp",
        exception=RuntimeError("Unexpected thread panic"),
    )
    assert res_exc.status == ToolStatus.INFRASTRUCTURE_ERROR
    assert res_exc.exit_code is None
    assert "RuntimeError" in res_exc.execution_error


def test_execute_tool_runner_with_mocked_subprocess():
    """Test execute_tool helper with mocked subprocess.run simulating return codes and exceptions."""
    # 1. Simulate exit code 0
    mock_res_0 = MagicMock(returncode=0, stdout="Success output", stderr="")
    with patch("subprocess.run", return_value=mock_res_0):
        res = execute_tool(["ruff", "check"], cwd="/tmp", tool_name="ruff")
        assert res.status == ToolStatus.PASS
        assert res.exit_code == 0
        assert res.stdout == "Success output"

    # 2. Simulate FileNotFoundError
    with patch("subprocess.run", side_effect=FileNotFoundError("ruff not found")):
        res = execute_tool(["ruff", "check"], cwd="/tmp", tool_name="ruff")
        assert res.status == ToolStatus.INFRASTRUCTURE_ERROR
        assert res.exit_code is None
        assert "FileNotFoundError" in res.execution_error

    # 3. Simulate TimeoutExpired
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="pytest", timeout=5.0)):
        res = execute_tool(["pytest"], cwd="/tmp", tool_name="pytest")
        assert res.status == ToolStatus.INFRASTRUCTURE_ERROR
        assert res.exit_code is None
        assert "TimeoutExpired" in res.execution_error
