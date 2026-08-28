"""
Secure execution sandbox helper for running generated code in isolated environments.
Restricts environment variables, enforces timeouts, and cleans up resource usage.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any, TypedDict

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExecutionResult(TypedDict):
    passed: bool
    exit_code: int | None
    stdout: str
    stderr: str
    execution_time: float
    timeout_triggered: bool


class SecureExecutor:
    """
    Executes Python scripts/commands in a restricted process-level sandbox.
    Enforces process timeouts and environment variable isolation.
    """

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    def get_clean_env(self) -> dict[str, str]:
        """
        Builds a sanitized environment dictionary that excludes application secrets.
        Allows only standard system paths and python paths.
        """
        # White-listed basic environment variables
        allowed_keys = {
            "PATH",
            "PYTHONPATH",
            "SYSTEMROOT",
            "SYSTEMDRIVE",
            "PATHEXT",
            "WINDIR",
            "TEMP",
            "TMP",
            "USERPROFILE",
            "HOME",
            "LANG",
            "LC_ALL",
        }
        
        clean_env = {}
        for key in allowed_keys:
            val = os.environ.get(key)
            if val is not None:
                clean_env[key] = val

        # Ensure minimal isolation: do NOT leak credentials
        # We explicitly verify these are absent
        sensitive_substrings = ["key", "secret", "token", "password", "db", "groq", "database", "url"]
        for k in list(clean_env.keys()):
            if any(sub in k.lower() for sub in sensitive_substrings):
                clean_env.pop(k, None)

        return clean_env

    async def execute_command(self, cmd: list[str], cwd: Path) -> ExecutionResult:
        """
        Executes a subprocess command in the given directory with a strict timeout and isolated environment.
        """
        start = time.perf_counter()
        clean_env = self.get_clean_env()
        
        logger.info("Executing secure command: %s (cwd=%s, timeout=%s)", " ".join(cmd), cwd, self.timeout)
        
        proc = None
        timeout_triggered = False
        exit_code = None
        stdout = ""
        stderr = ""

        try:
            # Create subprocess with piped outputs
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(cwd),
                env=clean_env,
            )

            # Wait for completion with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.timeout
                )
                stdout = stdout_bytes.decode(errors="ignore")
                stderr = stderr_bytes.decode(errors="ignore")
                exit_code = proc.returncode
            except asyncio.TimeoutError:
                logger.warning("Secure command execution timed out after %s seconds. Terminating...", self.timeout)
                timeout_triggered = True
                
                # Attempt to terminate the process
                try:
                    proc.terminate()
                    # Wait briefly for process to terminate
                    stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=3.0)
                    stdout = stdout_bytes.decode(errors="ignore") + "\n[Process terminated due to timeout]"
                    stderr = stderr_bytes.decode(errors="ignore")
                except Exception:
                    # Force kill if termination fails
                    try:
                        proc.kill()
                        await proc.wait()
                    except Exception:
                        pass
                    stdout = "[Process killed due to timeout]"
                    stderr = "Execution exceeded timeout limit."
                
                exit_code = -1

        except Exception as e:
            logger.exception("Subprocess execution exception: %s", e)
            stdout = ""
            stderr = f"Sandbox Executor Exception: {e}"
            exit_code = -1
            if proc:
                try:
                    proc.kill()
                    await proc.wait()
                except Exception:
                    pass

        duration = round(time.perf_counter() - start, 2)
        passed = (exit_code == 0) and not timeout_triggered

        return {
            "passed": passed,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "execution_time": duration,
            "timeout_triggered": timeout_triggered,
        }
