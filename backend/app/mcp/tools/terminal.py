"""
Terminal MCP Tool.

Executes safe terminal commands within the project workspace.
- Allow-list based command validation
- Execution timeout enforcement
- Working directory locked to workspace
"""

from __future__ import annotations

import asyncio
import shlex
import platform
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.mcp.registry import ToolRegistry, ToolDefinition

logger = get_logger(__name__)

# Allow-list of safe commands (prefix-matched)
_ALLOWED_COMMANDS = [
    "pwd",
    "ls",
    "dir",
    "echo",
    "cat",
    "type",
    "where",
    "which",
    "whoami",
    "hostname",
    "git status",
    "git log",
    "git branch",
    "git diff",
    "git remote",
    "git tag",
    "python --version",
    "python -V",
    "python3 --version",
    "pip list",
    "pip show",
    "pip --version",
    "node --version",
    "npm --version",
    "npx --version",
]

# Explicitly blocked patterns
_BLOCKED_PATTERNS = [
    "rm ",
    "rm -",
    "del ",
    "rmdir",
    "format",
    "mkfs",
    "dd ",
    "sudo",
    "su ",
    "chmod",
    "chown",
    "kill",
    "pkill",
    "shutdown",
    "reboot",
    "curl",
    "wget",
    "pip install",
    "pip uninstall",
    "npm install",
    "npm uninstall",
    "apt",
    "yum",
    "brew",
    "powershell",
    "cmd /c",
    "eval",
    "exec",
    ">",
    ">>",
    "|",
    "&",
    ";",
    "$(",
    "`",
]


def _is_command_allowed(command: str) -> bool:
    """Check if a command is in the allow-list and not in the block-list."""
    cmd_lower = command.strip().lower()

    # Check block-list first
    for blocked in _BLOCKED_PATTERNS:
        if blocked in cmd_lower:
            return False

    # Check allow-list
    for allowed in _ALLOWED_COMMANDS:
        if cmd_lower.startswith(allowed.lower()):
            return True

    return False


async def execute_command(command: str) -> dict[str, Any]:
    """
    Execute a safe terminal command within the workspace.

    Args:
        command: Shell command to execute. Must be in the allow-list.

    Returns:
        Dict with stdout, stderr, return code, and execution info.
    """
    if not command or not command.strip():
        raise ValueError("Command cannot be empty.")

    if not _is_command_allowed(command):
        raise PermissionError(
            f"Command not allowed: '{command}'. "
            f"Only safe commands are permitted: {', '.join(_ALLOWED_COMMANDS[:10])}..."
        )

    settings = get_settings()
    workspace = settings.mcp_workspace_path
    timeout = settings.mcp_terminal_timeout

    logger.info("Terminal executing: %s (cwd=%s, timeout=%ds)", command, workspace, timeout)

    try:
        is_windows = platform.system() == "Windows"

        if is_windows:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )
        else:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=workspace,
            )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            raise TimeoutError(f"Command timed out after {timeout}s: {command}")

        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        # Truncate very long output
        if len(stdout_str) > 50_000:
            stdout_str = stdout_str[:50_000] + "\n... [output truncated]"

        return {
            "command": command,
            "stdout": stdout_str,
            "stderr": stderr_str,
            "return_code": process.returncode,
            "success": process.returncode == 0,
        }

    except TimeoutError:
        raise
    except Exception as e:
        raise RuntimeError(f"Failed to execute command: {str(e)}")


def register_terminal_tools() -> None:
    """Register terminal tools with the MCP registry."""
    registry = ToolRegistry.instance()

    registry.register(ToolDefinition(
        name="terminal.execute_command",
        description=(
            "Execute a safe terminal command within the workspace. "
            "Only allow-listed commands like pwd, ls, dir, git status, python --version are permitted."
        ),
        category="terminal",
        parameters={
            "properties": {
                "command": {
                    "type": "string",
                    "description": "Shell command to execute (must be in the allow-list).",
                },
            },
            "required": ["command"],
        },
        handler=execute_command,
    ))

    logger.info("Terminal tools registered")
