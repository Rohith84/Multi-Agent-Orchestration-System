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
            "You are the Coder Agent. Your job is to output clean, well-structured, production-ready code.\n"
            "Whenever outputting files, specify the relative path at the start of code blocks using the format:\n"
            "```python filepath=\"app/main.py\"\n"
            "# code here\n"
            "```\n\n"
            "If a Bug Report is provided, carefully fix the failing file and error stack trace."
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
