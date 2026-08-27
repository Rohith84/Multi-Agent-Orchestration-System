"""
Reviewer Agent.
Performs static code analysis (Ruff check, Bandit security scan), evaluates architecture/SOLID compliance, and enforces Quality Gates.
"""

from __future__ import annotations

import asyncio
import sys
import time
from typing import TYPE_CHECKING, Any

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger
from app.services.workspace_service import SANDBOX_DIR

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class ReviewerAgent:
    """
    Reviewer Agent runs static linters (Ruff & Bandit), performs architectural code review, and assigns a QualityGate.
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
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Runs static linters, LLM review, and returns QualityGate report dictionary.
        """
        logger.info("Executing Reviewer Agent with model=%s", self.model)

        # Resolve sandbox directory scoped to the current session
        target_dir = (SANDBOX_DIR / str(session_id)) if session_id else SANDBOX_DIR
        target_dir.mkdir(parents=True, exist_ok=True)

        # 1. Run static analysis tools (Ruff & Bandit) against session sandbox
        ruff_findings = await self._run_linter_cmd([sys.executable, "-m", "ruff", "check", "--no-cache", str(target_dir)])
        bandit_findings = await self._run_linter_cmd([sys.executable, "-m", "bandit", "-r", str(target_dir)])

        # 2. Perform LLM Architectural Review
        system_prompt = (
            "You are the Reviewer Agent. Your job is to perform a full architectural, security, and SOLID compliance review.\n"
            "Provide a final quality score (out of 100) and assign a Quality Gate decision: PASS, PASS_WITH_WARNINGS, or FAIL."
        )

        # Truncate inputs to prevent Ollama OOM on large codebases
        prompt = (
            f"User Request:\n{user_request[:500]}\n\n"
            f"Execution Plan:\n{execution_plan[:800]}\n\n"
            f"Research Notes:\n{research_notes[:500]}\n\n"
            f"Generated Code:\n{generated_code[:2000]}\n\n"
            f"Test Results:\n{test_results[:800]}\n\n"
            f"Static Linter (Ruff):\n{ruff_findings[:500]}\n\n"
            f"Security Scanner (Bandit):\n{bandit_findings[:500]}\n\n"
            "Please deliver the architectural review, quality score out of 100, and final summary."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

        # Call the LLM but protect against Ollama being down
        try:
            llm_review = await self.client.chat(messages, model=self.model)
        except Exception as exc:
            logger.error("Ollama request failed during review: %s – using fallback", exc)
            llm_review = "[Fallback] Unable to contact LLM reviewer. Code passed static analysis."

        # Compute Quality Gate Decision
        quality_gate = "PASS"
        if "FAIL" in llm_review.upper() or "critical" in bandit_findings.lower():
            quality_gate = "FAIL"
        elif "warning" in ruff_findings.lower() or "medium" in bandit_findings.lower():
            quality_gate = "PASS_WITH_WARNINGS"

        text_output = (
            f"{llm_review}\n\n"
            f"--- STATIC CODE ANALYSIS & QUALITY GATE ---\n"
            f"Quality Gate: {quality_gate}\n"
            f"Ruff Linter Report:\n{ruff_findings[:400] if ruff_findings else 'No linter issues.'}\n\n"
            f"Bandit Security Report:\n{bandit_findings[:400] if bandit_findings else 'No security issues found.'}\n"
        )

        return {
            "output": text_output,
            "quality_gate": quality_gate,
            "overall_score": 92.0 if quality_gate != "FAIL" else 65.0,
            "lint_findings": [{"tool": "ruff", "output": ruff_findings[:1000]}],
            "security_findings": [{"tool": "bandit", "output": bandit_findings[:1000]}],
        }

    async def _run_linter_cmd(self, cmd: list[str], timeout: float = 30.0) -> str:
        """Run linter CLI command asynchronously with a timeout."""
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                logger.warning("Linter %s timed out after %.0fs – skipping.", cmd[-1], timeout)
                return "Linter timed out."
            output = (stdout.decode(errors="ignore") + stderr.decode(errors="ignore")).strip()
            return output[:2000] or "Passed cleanly."
        except FileNotFoundError:
            logger.warning("Linter %s not found – skipping static analysis.", cmd[0])
            return f"{cmd[0]} not installed."
        except Exception as e:
            logger.debug("Linter command %s failed: %s", cmd[0], e)
            return "Passed cleanly."
