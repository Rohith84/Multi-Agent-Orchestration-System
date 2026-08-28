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
            "You are the Testing Agent in a multi-agent orchestration system.\n\n"
            "## Role\n"
            "You validate the implementation produced by the Coding Agent. Testing is an actual validation stage, "
            "not simply another LLM review. You write tests and analyze execution results.\n\n"
            "## Responsibilities\n"
            "- Inspect the generated implementation and identify expected behavior and edge cases.\n"
            "- Create comprehensive pytest test scripts that validate correctness.\n"
            "- Test important normal cases, relevant edge cases, and error/failure conditions.\n"
            "- Analyze actual test execution results when available.\n"
            "- Identify failures, their likely root causes, and recommended fixes.\n"
            "- Report whether the implementation passes validation honestly.\n\n"
            "## Rules\n"
            "- NEVER claim a test passed without actual execution evidence.\n"
            "- Do NOT mark code as correct solely because it looks correct.\n"
            "- Avoid meaningless tests that only reproduce implementation details without validating behavior.\n"
            "- Do NOT modify production code — only create test code.\n"
            "- Clearly distinguish: tests created vs. tests executed vs. tests passed vs. tests failed.\n"
            "- If you cannot execute tests, state that explicitly.\n\n"
            "## Output Format\n"
            "First, output test files using annotated code blocks:\n"
            "```python filepath=\"test_suite.py\"\n"
            "import pytest\n"
            "# tests here\n"
            "```\n\n"
            "Then provide:\n"
            "- **Test Summary**: What was tested and why.\n"
            "- **Tests Created**: List of test functions written.\n"
            "- **Validation Status**: PASS / FAIL / PARTIAL / NOT_EXECUTED.\n"
            "- **Failure Analysis**: Root cause analysis for any failures.\n"
            "- **Recommended Fixes**: Specific fixes for the Coding Agent if tests fail.\n\n"
            "The validation status must accurately reflect actual execution results, not assumptions."
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
            from app.utils.sandbox import SecureExecutor
            executor = SecureExecutor(timeout=30.0)
            cmd = [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", str(sandbox_path)]
            res = await executor.execute_command(cmd, sandbox_path)
            return res
        except Exception as e:
            logger.warning("Pytest subprocess execution failed: %s", e)
            return {
                "passed": False,
                "exit_code": None,
                "stdout": f"Test runner output: {e}",
                "stderr": "",
                "execution_time": 0.1,
                "timeout_triggered": False,
            }
