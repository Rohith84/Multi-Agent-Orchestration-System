"""
Coder Agent.
Synthesizes source code following the execution plan and research guidelines.
May read project files via MCP filesystem tool.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class CoderAgent:
    """
    Coder Agent outputs the actual software implementation (code scripts, structures).
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
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        logger.info("Executing Coder Agent with model=%s", self.model)

        # MCP Tool: Read relevant project files for context
        file_context = ""
        if tool_runner:
            try:
                # Search for Python files to understand existing patterns
                search_result = await tool_runner.run_tool(
                    "filesystem.search_files",
                    {"pattern": "*.py", "path": "backend/app"},
                )
                if search_result:
                    files = search_result.get("matches", [])[:5]
                    if files:
                        file_list = "\n".join(f"  - {f['path']}" for f in files)
                        file_context = f"\n\nExisting Project Files:\n{file_list}"
            except Exception as e:
                logger.debug("Coder MCP tool failed (non-critical): %s", e)

        system_prompt = (
            "You are the Coder Agent. Your job is to output clean, well-structured, production-ready source code "
            "based on the user request, the plan, and the research notes provided.\n\n"
            "Include inline comments and docstrings. Provide the complete code blocks without placeholders. "
            "Ensure you address code structure and correct syntax."
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Research Notes:\n{research_notes}\n\n"
        )
        if file_context:
            prompt += f"{file_context}\n\n"
        prompt += "Please generate the complete source code implementation."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
