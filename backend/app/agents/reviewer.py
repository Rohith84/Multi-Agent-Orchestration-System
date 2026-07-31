"""
Reviewer Agent.
Reviews final code, checks architectural patterns, and scores the quality.
Includes sources and citations in the review assessment.
May inspect repository and architecture via MCP tools.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class ReviewerAgent:
    """
    Reviewer Agent reviews the whole process outputs, checks SOLID/security rules,
    includes document citations from research notes, and returns audit checklists + quality score.
    """

    def __init__(self, client: OllamaClient) -> None:
        self.client = client
        self.settings = get_settings()
        self.model = self.settings.model_reviewer

    async def execute(
        self,
        user_request: str,
        execution_plan: str,
        generated_code: str,
        test_results: str,
        research_notes: str = "",
        tool_runner: MCPToolRunner | None = None,
    ) -> str:
        logger.info("Executing Reviewer Agent with model=%s", self.model)

        # MCP Tool: Inspect project architecture for review context
        architecture_context = ""
        if tool_runner:
            try:
                result = await tool_runner.run_tool(
                    "filesystem.list_directory",
                    {"path": "backend/app"},
                )
                if result:
                    entries = result.get("entries", [])
                    dirs = [e["name"] for e in entries if e["type"] == "directory"]
                    if dirs:
                        architecture_context = (
                            f"\n\nProject Architecture (backend/app modules): {', '.join(dirs)}"
                        )
            except Exception as e:
                logger.debug("Reviewer MCP tool failed (non-critical): %s", e)

        system_prompt = (
            "You are the Reviewer Agent. Your job is to review the user's initial request, "
            "the plan, the generated code, the test results, and the research notes (including retrieved documents and context).\n"
            "Perform a full review of architecture, security, readability, and SOLID principles.\n"
            "You MUST verify that code aligns with the research details. Provide clear citations of the documents, "
            "files, or guidelines that were retrieved in the Research Notes.\n"
            "Deliver a structured audit checklist, citations list, and an overall quality score out of 100.\n\n"
            "Outline:\n"
            "1. Architectural & SOLID Compliance\n"
            "2. Readability & Maintainability Audit\n"
            "3. Security Check\n"
            "4. Citations & Sources (list document filenames and details here)\n"
            "5. Final Quality Score (e.g. Quality Score: 95/100)\n"
            "6. Brief Summary Response for the user"
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Research Notes (with retrieved documents context):\n{research_notes}\n\n"
            f"Generated Code:\n{generated_code}\n\n"
            f"Test Results:\n{test_results}\n\n"
        )
        if architecture_context:
            prompt += f"{architecture_context}\n\n"
        prompt += (
            "Please conduct the final review, list citations/references, provide the scoring, and write a summary response."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        response = await self.client.chat(messages, model=self.model)
        return response
