"""
Tester Agent.
Detects bugs, verifies syntax, and generates unit test configurations.
May inspect environment via MCP terminal tool.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class TesterAgent:
    """
    Tester Agent analyzes generated code for security/syntax flaws and generates unit tests.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_tester

    async def execute(
        self,
        generated_code: str,
        execution_plan: str,
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        logger.info("Executing Tester Agent with model=%s", self.model)

        # MCP Tool: Check Python version and installed packages
        env_context = ""
        if tool_runner:
            try:
                result = await tool_runner.run_tool(
                    "terminal.execute_command",
                    {"command": "python --version"},
                )
                if result and result.get("success"):
                    env_context += f"\nPython Version: {result['stdout']}"
            except Exception as e:
                logger.debug("Tester MCP terminal tool failed (non-critical): %s", e)

        system_prompt = (
            "You are the Tester Agent. Your job is to analyze the generated code for syntax, logic errors, "
            "and security issues, suggest fixes, and generate unit tests (e.g. pytest or equivalent).\n\n"
            "Outline:\n"
            "1. Code Quality & Bug Analysis\n"
            "2. Suggested Fixes / Code Improvements\n"
            "3. Complete Unit Tests (with assert checks)"
        )

        prompt = (
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Generated Code:\n{generated_code}\n\n"
        )
        if env_context:
            prompt += f"Environment Info:{env_context}\n\n"
        prompt += "Please test this implementation and provide quality feedback and unit test scripts."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
