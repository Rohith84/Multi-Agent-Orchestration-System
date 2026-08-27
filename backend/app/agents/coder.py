"""
Coder Agent.
Synthesizes source code, persists multi-file structures to disk in sandbox_workspace/, and performs automatic code repair upon test failures.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.workspace_service import WorkspaceService

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class CoderAgent:
    """
    Coder Agent outputs source code, writes files to disk, and handles automated bug repair.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_coder

    async def execute(
        self,
        user_request: str,
        execution_plan: str,
        research_notes: str,
        bug_report: dict[str, Any] | None = None,
        workspace_service: WorkspaceService | None = None,
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        logger.info("Executing Coder Agent with model=%s", self.model)

        system_prompt = (
            "You are the Coding Agent in a multi-agent orchestration system.\n\n"
            "## Role\n"
            "You implement the requested software changes based on the user's requirements, the Planner's execution plan, "
            "and the Research Agent's context. You do NOT plan, research, test, or review — you write code.\n\n"
            "## Responsibilities\n"
            "- Generate or modify code according to the execution plan and research notes.\n"
            "- Follow existing project architecture and conventions.\n"
            "- Reuse existing components whenever possible rather than creating duplicates.\n"
            "- Handle errors and edge cases appropriately.\n"
            "- Produce implementation that can be validated by the Testing Agent.\n"
            "- Keep changes minimal and focused on the requested task.\n\n"
            "## Rules\n"
            "- Do NOT redesign the architecture unless the plan explicitly requires it.\n"
            "- Do NOT invent files, modules, or dependencies that are not in the plan or research context.\n"
            "- Do NOT silently change unrelated functionality.\n"
            "- Do NOT claim code has been tested — that is the Testing Agent's job.\n"
            "- Follow the language, framework, and conventions of the existing project.\n"
            "- Consider security implications of generated code.\n"
            "- If requirements are ambiguous, identify the ambiguity explicitly rather than inventing requirements.\n\n"
            "## Output Format\n"
            "For every file you create or modify, use annotated code blocks with the filepath:\n"
            "```python filepath=\"path/to/file.py\"\n"
            "# implementation here\n"
            "```\n\n"
            "After all code blocks, provide:\n"
            "- **Implementation Summary**: What was implemented and why.\n"
            "- **Dependencies Added**: Any new libraries or packages required.\n"
            "- **Assumptions**: Any assumptions made due to incomplete information.\n"
            "- **Potential Risks**: Known limitations or areas that need attention.\n\n"
            "If a Bug Report is provided from a previous test failure, carefully analyze the stack trace and fix "
            "the specific failing code. Focus on the root cause, not symptoms."
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Research Notes:\n{research_notes}\n\n"
        )

        if bug_report:
            prompt += (
                f"\n--- AUTOMATED TEST FAILURE REPAIR REQUEST ---\n"
                f"Failed File: {bug_report.get('failed_file', 'unknown')}\n"
                f"Failed Test: {bug_report.get('failed_test', 'unknown')}\n"
                f"Stack Trace:\n{bug_report.get('stack_trace', '')[:1000]}\n"
                f"Suggested Fix: {bug_report.get('suggested_fix', '')}\n"
                f"Please fix the implementation code to resolve these test failures.\n\n"
            )
        else:
            prompt += "Please generate the complete source code implementation.\n"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        response = await self.client.chat(messages, model=self.model)

        # Parse and persist files to disk if WorkspaceService is available
        if workspace_service:
            try:
                await self._persist_parsed_files(response, workspace_service)
            except Exception as e:
                logger.warning("Failed persisting coder files to disk: %s", e)

        return response

    async def _persist_parsed_files(self, response_text: str, workspace_service: WorkspaceService) -> None:
        """Parse code blocks with filepath annotations and write them to disk."""
        pattern = r"```([a-zA-Z0-9_-]*)\s+(?:filepath|file)=[\"']?([^\"'\s\n>]+)[\"']?\n(.*?)```"
        matches = re.findall(pattern, response_text, re.DOTALL)

        if not matches:
            # Fallback: Save entire output to main.py if no annotated code blocks
            await workspace_service.write_file("main.py", response_text, "python")
            return

        for lang, rel_path, content in matches:
            clean_lang = lang.strip().lower() or "python"
            clean_path = rel_path.strip().lstrip("/\\")
            await workspace_service.write_file(clean_path, content.strip(), clean_lang)
            logger.info("Persisted generated file to workspace: %s (%s)", clean_path, clean_lang)
