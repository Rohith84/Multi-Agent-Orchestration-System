"""
Structured Tool Execution Result and Diagnostic Classification Schema.

Defines:
- ToolStatus (enum)
- ToolResult (Pydantic model)
- classify_tool_result (deterministic status classifier)
- execute_tool (subprocess execution runner returning ToolResult)
"""

from __future__ import annotations

import os
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolStatus(str, Enum):
    """Execution status for deterministic tool classification."""

    PASS = "PASS"
    LINT_FAILURE = "LINT_FAILURE"
    TEST_FAILURE = "TEST_FAILURE"
    CONFIG_ERROR = "CONFIG_ERROR"
    INFRASTRUCTURE_ERROR = "INFRASTRUCTURE_ERROR"


class ToolResult(BaseModel):
    """Structured deterministic tool execution result."""

    tool: str = Field(..., description="Name of the tool executed (e.g. 'ruff', 'pytest')")
    command: list[str] = Field(..., description="Exact command line arguments executed")
    cwd: str = Field(..., description="Working directory of execution")
    exit_code: int | None = Field(
        default=None,
        description="Subprocess exit code, or None for infrastructure failures",
    )
    stdout: str = Field(default="", description="Exact standard output captured")
    stderr: str = Field(default="", description="Exact standard error captured")
    execution_error: str | None = Field(
        default=None,
        description="Exception message or error details if process execution failed",
    )
    duration_ms: float = Field(..., description="Execution duration in milliseconds")
    status: ToolStatus = Field(..., description="Deterministic status classification")

    model_config = ConfigDict(use_enum_values=True)


def classify_tool_result(
    tool: str,
    command: list[str],
    cwd: str,
    exit_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
    exception: Exception | str | None = None,
    duration_ms: float = 0.0,
) -> ToolResult:
    """
    Deterministically classify a tool execution into a ToolResult.

    Classification rules:
    1. Infrastructure failure:
       FileNotFoundError, PermissionError, TimeoutExpired, OSError when process cannot execute,
       or any exception raised prior to getting exit code.
       -> INFRASTRUCTURE_ERROR with exit_code = None, exception details in execution_error.
    2. exit_code == 0 -> PASS
    3. exit_code == 1 & (Ruff / linter command) -> LINT_FAILURE
    4. exit_code == 1 & (Pytest / test command) -> TEST_FAILURE
    5. exit_code == 2 -> CONFIG_ERROR
    6. Non-standard or unknown exit code -> deterministic status based on tool/command indicators or CONFIG_ERROR.
    """
    exec_err_str: str | None = None
    is_infra = False

    if isinstance(exception, Exception):
        is_infra = True
        exec_err_str = f"{type(exception).__name__}: {exception}" if str(exception) else type(exception).__name__
    elif isinstance(exception, str) and exception:
        is_infra = True
        exec_err_str = exception
    elif exit_code is None:
        is_infra = True

    if is_infra:
        status = ToolStatus.INFRASTRUCTURE_ERROR
        exit_code = None
    elif exit_code == 0:
        status = ToolStatus.PASS
    elif exit_code == 2:
        status = ToolStatus.CONFIG_ERROR
    elif exit_code == 1:
        tool_lower = tool.lower()
        cmd_str = " ".join(command).lower()
        if "ruff" in tool_lower or "ruff" in cmd_str or "lint" in tool_lower or "lint" in cmd_str:
            status = ToolStatus.LINT_FAILURE
        elif "pytest" in tool_lower or "pytest" in cmd_str or "test" in tool_lower or "test" in cmd_str:
            status = ToolStatus.TEST_FAILURE
        else:
            status = ToolStatus.CONFIG_ERROR
    else:
        # Exit code > 2 or unknown non-zero exit code
        tool_lower = tool.lower()
        cmd_str = " ".join(command).lower()
        if "ruff" in tool_lower or "ruff" in cmd_str or "lint" in tool_lower or "lint" in cmd_str:
            status = ToolStatus.LINT_FAILURE
        elif "pytest" in tool_lower or "pytest" in cmd_str or "test" in tool_lower or "test" in cmd_str:
            status = ToolStatus.TEST_FAILURE
        else:
            status = ToolStatus.CONFIG_ERROR

    return ToolResult(
        tool=tool,
        command=command,
        cwd=cwd,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        execution_error=exec_err_str,
        duration_ms=round(duration_ms, 2),
        status=status,
    )


def execute_tool(
    cmd: list[str],
    cwd: str | Path | None = None,
    timeout: float = 30.0,
    tool_name: str | None = None,
) -> ToolResult:
    """
    Run a CLI tool command synchronously using subprocess.run and return a structured ToolResult.

    Preserves exact stdout, stderr, exit code, command, cwd, duration_ms, and exception information.
    """
    working_dir = str(cwd) if cwd else os.getcwd()
    name = tool_name or (cmd[0] if cmd else "unknown")
    start_time = time.perf_counter()

    try:
        res = subprocess.run(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return classify_tool_result(
            tool=name,
            command=cmd,
            cwd=working_dir,
            exit_code=res.returncode,
            stdout=res.stdout,
            stderr=res.stderr,
            duration_ms=duration_ms,
        )
    except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired, OSError, Exception) as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return classify_tool_result(
            tool=name,
            command=cmd,
            cwd=working_dir,
            exit_code=None,
            stdout="",
            stderr="",
            exception=exc,
            duration_ms=duration_ms,
        )
