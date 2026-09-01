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
            "## Completeness Rules (CRITICAL)\n"
            "- Generate EVERY file listed in the Planner's File Manifest. If a file is in the manifest, you MUST produce it.\n"
            "- Every code block MUST be syntactically complete and runnable — no placeholders like '# ... rest of code', "
            "no 'TODO: implement', no '# add more here', no cutting off mid-function.\n"
            "- Every file MUST end with a complete statement — NEVER cut off mid-line or mid-function.\n"
            "- Include ALL dependency files: requirements.txt, package.json, .env.example, database init scripts.\n"
            "- Sort all Python imports in isort-compatible order: stdlib → third-party → local.\n"
            "- For full-stack apps, always include: models, schemas/Pydantic, API routes, service layer, "
            "database initialization, and a minimal working frontend.\n"
            "- Include proper error handling (try/except, HTTPException with status codes) in all API endpoints.\n"
            "## Strict Narrative vs Code Block Separation Rules (CRITICAL)\n"
            "- Place ALL narrative explanations, implementation summaries, reasoning, and prose text OUTSIDE code blocks.\n"
            "- Code blocks MUST contain ONLY valid executable source code (starting directly with imports or code statements).\n"
            "- NEVER put markdown headings (e.g. `### Implementation Summary`), prose descriptions, or review/test summaries INSIDE code blocks.\n"
            "- EVERY code block MUST specify its target relative file path using `filepath=\"...\"`:\n"
            "  ```python filepath=\"app/main.py\"\n"
            "  from fastapi import FastAPI\n"
            "  # valid python code only\n"
            "  ```\n\n"
            "## Test Isolation & Determinism Rules (CRITICAL for test files)\n"
            "- If you generate unit test files (`test_suite.py` or `tests/test_*.py`), tests MUST be isolated and independent.\n"
            "- DO NOT hardcode static database IDs (e.g. ID 1). Always create test items dynamically via POST inside each test and extract the returned ID before testing GET, PUT, or DELETE endpoints.\n"
            "- DO NOT assume pre-existing database records.\n\n"
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
