"""
Tester Agent.
Detects project framework, executes unit tests (pytest / unittest), captures logs, and builds structured BugReports for self-repair loops.
"""

from __future__ import annotations

import asyncio
import re
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.workspace_service import WorkspaceService, SANDBOX_DIR

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class TesterAgent:
    """
    Tester Agent runs real test suites, captures execution output, and builds bug reports.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_tester

    async def execute(
        self,
        generated_code: str,
        execution_plan: str,
        workspace_service: WorkspaceService | None = None,
        tool_runner: MCPToolRunner | None = None,
    ) -> dict[str, Any]:
        """
        Execute tests and return detailed results dictionary with text output, status, and bug report.
        """
        logger.info("Executing Tester Agent with model=%s", self.model)

        # 1. Ask LLM to analyze code & generate pytest test script
        system_prompt = (
            "You are the Tester Agent. Your job is to analyze the generated code and write complete, executable pytest unit tests.\n"
            "Format the test script block as:\n"
            "```python filepath=\"test_suite.py\"\n"
            "import pytest\n"
            "# tests here\n"
            "```"
        )

        prompt = (
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Generated Code:\n{generated_code}\n\n"
            "Please generate complete pytest unit test scripts."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        llm_analysis = await self.client.chat(messages, model=self.model)

        # Write test files to workspace sandbox if available
        if workspace_service:
            pattern = r"```([a-zA-Z0-9_-]*)\s+(?:filepath|file)=[\"']?([^\"'\s\n>]+)[\"']?\n(.*?)```"
            matches = re.findall(pattern, llm_analysis, re.DOTALL)
            for lang, rel_path, content in matches:
                if "test" in rel_path.lower():
                    await workspace_service.write_file(rel_path.strip(), content.strip(), "python")

        # 2. Run real pytest test execution against sandbox workspace
        test_run_res = await self._run_pytest_subprocess(workspace_service)

        passed = test_run_res["passed"]
        bug_report = None

        if not passed:
            bug_report = {
                "failed_file": str((workspace_service.workspace_dir if workspace_service else SANDBOX_DIR) / "main.py"),
                "failed_test": "test_suite.py",
                "stack_trace": test_run_res["stderr"] or test_run_res["stdout"],
                "error_category": "AssertionError",
                "suggested_fix": "Fix implementation logic based on captured test output.",
                "severity": "HIGH",
            }

        text_output = (
            f"{llm_analysis}\n\n"
            f"--- REAL PYTEST EXECUTION RESULT ---\n"
            f"Status: {'PASSED' if passed else 'FAILED'}\n"
            f"Execution Time: {test_run_res['execution_time']}s\n"
            f"Stdout:\n{test_run_res['stdout'][:800]}\n"
            f"Stderr:\n{test_run_res['stderr'][:800]}\n"
        )

        return {
            "output": text_output,
            "passed": passed,
            "execution_time": test_run_res["execution_time"],
            "stdout": test_run_res["stdout"],
            "stderr": test_run_res["stderr"],
            "bug_report": bug_report,
        }

    async def _run_pytest_subprocess(self, workspace_service: WorkspaceService | None = None) -> dict[str, Any]:
        """Execute pytest against sandbox_workspace/ via subprocess."""
        start = time.time()
        sandbox_path = (workspace_service.workspace_dir if workspace_service else SANDBOX_DIR).resolve()

        if not sandbox_path.exists():
            sandbox_path.mkdir(parents=True, exist_ok=True)

        test_files = list(sandbox_path.rglob("test_*.py")) + list(sandbox_path.rglob("*_test.py"))
        if not test_files:
            return {
                "passed": False,
                "exit_code": None,
                "stdout": "",
                "stderr": "No generated test files were found in the session workspace.",
                "execution_time": round(time.time() - start, 2),
            }

        try:
            cmd = [sys.executable, "-m", "pytest", str(sandbox_path)]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(sandbox_path),
            )
            stdout, stderr = await proc.communicate()
            duration = round(time.time() - start, 2)
            passed = (proc.returncode == 0)

            return {
                "passed": passed,
                "exit_code": proc.returncode,
                "stdout": stdout.decode(errors="ignore"),
                "stderr": stderr.decode(errors="ignore"),
                "execution_time": duration,
            }
        except Exception as e:
            logger.warning("Pytest subprocess execution failed: %s", e)
            return {
                "passed": False,
                "exit_code": None,
                "stdout": f"Test runner output: {e}",
                "stderr": "",
                "execution_time": 0.1,
            }
