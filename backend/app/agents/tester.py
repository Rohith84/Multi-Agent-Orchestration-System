"""
Tester Agent.
Generates comprehensive test scripts, writes them to the workspace, and analyzes test coverage quality.
Does NOT execute tests — the Internal Quality Gate owns pytest execution.
"""

from __future__ import annotations

import re
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
    Tester Agent generates test scripts, writes them to the workspace sandbox,
    and analyzes test coverage quality. It does NOT execute tests — the Internal
    Quality Gate handles deterministic test execution.
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
        validation_results: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Generate test scripts, write to workspace, and analyze coverage quality.

        Args:
            generated_code: The code produced by the Coder Agent.
            execution_plan: The Planner's execution plan.
            workspace_service: Workspace to write test files into.
            tool_runner: MCP tool runner (optional).
            validation_results: Pre-computed Quality Gate results (if available from prior validation).

        Returns:
            Dictionary with 'output' (analysis text), 'tester_analysis' (coverage assessment).
        """
        logger.info("Executing Tester Agent with model=%s", self.model)

        # 1. Ask LLM to generate pytest test scripts
        system_prompt = (
            "You are the Testing Agent in a multi-agent orchestration system.\n\n"
            "## Role\n"
            "You generate comprehensive test suites and analyze test coverage quality. "
            "You do NOT execute tests — a separate deterministic Quality Gate handles test execution.\n\n"
            "## Responsibilities\n"
            "1. **Generate Tests**: Create comprehensive pytest test scripts that validate the implementation.\n"
            "2. **Analyze Coverage**: Assess whether the generated tests adequately cover the requirements.\n\n"
            "## Test Generation Rules\n"
            "- Create tests for all important functionality.\n"
            "- Test success paths, failure paths, and edge cases.\n"
            "- Tests MUST be isolated and independent — no execution order dependencies.\n"
            "- DO NOT hardcode static database IDs (e.g., ID 1). Create test items dynamically.\n"
            "- DO NOT assume pre-existing database state.\n"
            "- Place all explanations OUTSIDE code blocks.\n"
            "- Code blocks MUST contain ONLY valid Python pytest source code.\n\n"
            "## Coverage Analysis Output\n"
            "After generating tests, provide a coverage analysis:\n"
            "- **Requirements Covered**: Which requirements from the plan are tested?\n"
            "- **Requirements NOT Covered**: Which requirements lack tests?\n"
            "- **Edge Cases Tested**: What edge cases are covered?\n"
            "- **Missing Edge Cases**: What edge cases are NOT covered?\n"
            "- **Test Isolation**: Are all tests properly isolated?\n"
            "- **Test Determinism**: Are tests deterministic (no randomness, no external dependencies)?\n"
            "- **Coverage Assessment**: ADEQUATE / PARTIAL / INSUFFICIENT\n\n"
            "## Output Format\n"
            "First, output test files using annotated code blocks:\n"
            "```python filepath=\"test_suite.py\"\n"
            "import pytest\n"
            "# tests here\n"
            "```\n\n"
            "Then provide the coverage analysis.\n"
        )

        prompt = (
            f"Execution Plan:\n{execution_plan[:2000]}\n\n"
            f"Generated Code:\n{generated_code[:3000]}\n\n"
            "Please generate comprehensive pytest unit test scripts and provide a coverage analysis."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        llm_analysis = await self.client.chat(messages, model=self.model, max_tokens=1800)

        # Write test files to workspace sandbox if available
        if workspace_service:
            from app.utils.artifact_extractor import extract_code_artifacts
            artifacts = extract_code_artifacts(llm_analysis)
            for artifact in artifacts:
                if "test" in artifact.path.lower() or artifact.path.endswith(".py"):
                    await workspace_service.write_file(artifact.path, artifact.content, artifact.language)

        # Build output text
        text_output = (
            f"{llm_analysis}\n\n"
            f"--- TESTER AGENT SUMMARY ---\n"
            f"Role: Test Generation & Coverage Analysis\n"
            f"Tests Generated: YES (written to workspace for Quality Gate execution)\n"
        )

        # If validation_results are available, include them in analysis context
        if validation_results:
            pytest_info = validation_results.get("pytest", {})
            text_output += (
                f"\n--- QUALITY GATE PYTEST EVIDENCE (read-only) ---\n"
                f"Pytest Status: {pytest_info.get('status', 'NOT_AVAILABLE')}\n"
                f"Pytest Output:\n{pytest_info.get('output', 'No output available')[:600]}\n"
            )

        return {
            "output": text_output,
            "tester_analysis": llm_analysis,
        }

    @staticmethod
    def _classify_error(output: str) -> str:
        """Classify the primary error type from pytest output."""
        error_patterns = [
            ("SyntaxError", "SyntaxError"),
            ("ModuleNotFoundError", "ModuleNotFoundError"),
            ("ImportError", "ImportError"),
            ("NameError", "NameError"),
            ("TypeError", "TypeError"),
            ("AttributeError", "AttributeError"),
            ("FileNotFoundError", "FileNotFoundError"),
            ("AssertionError", "AssertionError"),
            ("ValueError", "ValueError"),
            ("KeyError", "KeyError"),
        ]
        for pattern, category in error_patterns:
            if pattern in output:
                return category
        if "FAILED" in output:
            return "TestFailure"
        if "ERROR" in output:
            return "RuntimeError"
        return "Unknown"

    @staticmethod
    def _extract_failed_test(output: str) -> str:
        """Extract the name of the first failing test from pytest output."""
        # Match patterns like "FAILED test_file.py::test_name"
        match = re.search(r"FAILED\s+([\w/\\.-]+(?:::[\\w]+)?)", output)
        if match:
            return match.group(1)
        # Match patterns like "ERROR test_file.py"
        match = re.search(r"ERROR\s+([\w/\\.-]+)", output)
        if match:
            return match.group(1)
        return "test_suite.py"

    @staticmethod
    def _build_suggested_fix(error_category: str, output: str) -> str:
        """Build a specific fix suggestion based on error type."""
        suggestions = {
            "SyntaxError": "Fix the syntax error — check for unclosed brackets, missing colons, or incomplete statements near the reported line.",
            "ModuleNotFoundError": "Install the missing module or fix the import path. Ensure all dependencies are listed in requirements.txt.",
            "ImportError": "Fix the import — the referenced name may not exist in the module, or the module structure may be incorrect.",
            "NameError": "A variable or function is referenced before being defined. Check for typos or missing imports.",
            "TypeError": "A function is being called with wrong argument types or count. Check the function signature.",
            "AttributeError": "An object doesn't have the referenced attribute. Check the class definition or object type.",
            "FileNotFoundError": "A file path referenced in the code does not exist. Check file paths and ensure all required files are generated.",
            "AssertionError": "A test assertion failed — the actual output doesn't match the expected value. Fix the implementation logic.",
            "ValueError": "An invalid value was passed. Check input validation and type conversions.",
            "KeyError": "A dictionary key was not found. Ensure all expected keys exist in the data structure.",
        }
        base = suggestions.get(error_category, "Fix the implementation based on the test output above.")

        # Try to extract the specific error message for more context
        match = re.search(rf"{error_category}:\s*(.+?)(?:\n|$)", output)
        if match:
            base += f" Specific error: {match.group(1).strip()[:200]}"

        return base
