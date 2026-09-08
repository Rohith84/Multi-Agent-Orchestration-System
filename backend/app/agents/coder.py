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
        rag_result: dict[str, Any] | Any | None = None,
    ) -> str:
        logger.info("Executing Coder Agent with model=%s", self.model)

        system_prompt = (
            "You are the Coding Agent in a multi-agent orchestration system.\n\n"
            "## Role & Responsibilities\n"
            "You implement software changes based on the user's requirements, the Planner's plan, and the Research context.\n"
            "You do NOT execute tests or conduct final architectural reviews — you write clean, maintainable, complete source code.\n\n"
            "## Multi-File Consistency & Quality Rules (CRITICAL)\n"
            "- Ensure strict internal consistency across all generated files (matching function signatures, imports, Pydantic schemas, and routes).\n"
            "- Never import non-existent symbols, modules, or unlisted dependencies.\n"
            "- Ensure test files import actual generated module names and function signatures.\n"
            "- Reuse existing project abstractions, design patterns, and helper functions.\n"
            "- Do NOT claim that code was tested or validated — actual correctness is evaluated deterministically by CodeContract, Ruff, Pytest, Bandit, and Quality Gate.\n\n"
            "## Completeness Rules (CRITICAL)\n"
            "- Generate EVERY file listed in the Planner's File Manifest. If a file is in the manifest, you MUST produce it.\n"
            "- Every code block MUST be syntactically complete and runnable — NO placeholders like '# ... rest of code', "
            "NO 'TODO: implement', NO '# add more here', NO cutting off mid-function.\n"
            "- Include proper error handling (try/except, HTTPException status codes).\n"
            "- Sort all Python imports in isort-compatible order: stdlib → third-party → local.\n\n"
            "## Implementation Rationale & Structure\n"
            "Before code blocks, provide a concise structured implementation rationale summary:\n"
            "- **Implementation Decision**: Selected technical architecture and pattern.\n"
            "- **Evidence Used**: Research notes and requirements referenced.\n"
            "- **Why This Approach**: Technical justification for this design.\n"
            "- **Alternatives Considered**: Other options evaluated.\n"
            "- **Trade-offs & Risks**: Architectural trade-offs and potential edge-case risks.\n"
            "- **Implementation Implications**: How this impacts downstream components.\n\n"
            "## Strict Narrative vs Code Block Separation Rules (CRITICAL)\n"
            "- Place ALL narrative explanations, implementation summaries, and rationale OUTSIDE code blocks.\n"
            "- Code blocks MUST contain ONLY valid executable source code starting directly with imports or code statements.\n"
            "- NEVER put markdown headings, prose summaries, or comments containing placeholders INSIDE code blocks.\n"
            "- EVERY code block MUST specify its target relative file path using `filepath=\"...\"`:\n"
            "  ```python filepath=\"app/main.py\"\n"
            "  def add(a: int, b: int) -> int:\n"
            "      return a + b\n"
            "  ```\n\n"
            "If a Bug Report is provided from a previous test failure, carefully analyze the stack trace and fix "
            "the specific failing code. Focus on the root cause, not symptoms."
        )

        prompt = (
            f"User Request:\n{user_request}\n\n"
            f"Execution Plan:\n{execution_plan}\n\n"
            f"Research Notes:\n{research_notes}\n\n"
        )

        if rag_result:
            if isinstance(rag_result, dict):
                st_val = rag_result.get("status")
                err_msg = rag_result.get("error")
            else:
                st_val = getattr(rag_result, "status", None)
                err_msg = getattr(rag_result, "error", None)

            st_val_str = st_val.value if hasattr(st_val, "value") else str(st_val)
            if st_val_str == "RAG_INFRASTRUCTURE_ERROR":
                prompt += f"[RAG STATUS: RAG_INFRASTRUCTURE_ERROR] Knowledge Base search failed due to an infrastructure error: {err_msg or 'Vector DB error'}. Context is unavailable. Do NOT invent missing requirements or assume failure.\n\n"
            elif st_val_str == "RAG_EMPTY":
                prompt += "[RAG STATUS: RAG_EMPTY] Knowledge Base search succeeded, but returned 0 matching documents.\n\n"
            elif st_val_str == "RAG_SUCCESS":
                prompt += "[RAG STATUS: RAG_SUCCESS] Knowledge Base search succeeded and retrieved relevant project context.\n\n"
            else:
                prompt += f"[RAG STATUS: {st_val_str}]\n\n"

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
        """Parse clean code blocks and write artifacts to disk. Filters out markdown prose."""
        from app.utils.artifact_extractor import extract_code_artifacts

        artifacts = extract_code_artifacts(response_text)

        if not artifacts:
            logger.warning("No valid code artifacts found in Coder Agent output — skipping workspace write.")
            return

        for artifact in artifacts:
            await workspace_service.write_file(artifact.path, artifact.content, artifact.language)
            logger.info("Persisted clean generated artifact to workspace: %s (%s)", artifact.path, artifact.language)
