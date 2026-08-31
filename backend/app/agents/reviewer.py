"""
Reviewer Agent.
Performs qualitative architectural code review and enforces Quality Gate decisions.
Does NOT run Ruff/Bandit/Pytest — those are executed by the Internal Quality Gate.
Consumes pre-computed validation_results and provides qualitative assessment.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.mcp.clients.tool_runner import MCPToolRunner

logger = get_logger(__name__)


class ReviewerAgent:
    """
    Reviewer Agent performs qualitative architectural review and enforces Quality Gate decisions.
    Does NOT run linters or tests — consumes pre-computed validation_results from the Quality Gate.
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
        validation_results: dict[str, Any] | None = None,
        tester_analysis: str = "",
        tool_runner: MCPToolRunner | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Consumes Quality Gate evidence, evaluates LLM review against it, and returns QualityGate report.

        Args:
            validation_results: Pre-computed structured validation results from the Quality Gate.
                Contains ruff, pytest, bandit, deterministic_checks statuses and outputs.
            tester_analysis: Qualitative test coverage analysis from the Tester Agent.
        """
        logger.info("Executing Reviewer Agent with model=%s", self.model)

        # Extract pre-computed statuses from Quality Gate results (fail-closed defaults)
        if validation_results:
            ruff_status = validation_results.get("ruff", {}).get("status", "ERROR")
            pytest_status = validation_results.get("pytest", {}).get("status", "ERROR")
            bandit_status = validation_results.get("bandit", {}).get("status", "ERROR")
            det_status = validation_results.get("deterministic_checks", {}).get("status", "ERROR")
            authoritative_gate = validation_results.get("quality_gate", "FAIL")

            ruff_output = validation_results.get("ruff", {}).get("output", "No output")
            pytest_output = validation_results.get("pytest", {}).get("output", "No output")
            bandit_output = validation_results.get("bandit", {}).get("output", "No output")
        else:
            # No validation_results available → fail closed, not open
            ruff_status = "ERROR"
            pytest_status = "ERROR"
            bandit_status = "ERROR"
            det_status = "ERROR"
            authoritative_gate = "FAIL"
            ruff_output = "No validation results available (missing evidence)."
            pytest_output = "No validation results available (missing evidence)."
            bandit_output = "No validation results available (missing evidence)."

        # Compute authoritative decision label
        deterministic_failed = authoritative_gate == "FAIL"
        if deterministic_failed:
            final_decision_label = "REJECTED"
        elif authoritative_gate == "PASS_WITH_WARNINGS":
            final_decision_label = "APPROVED_WITH_WARNINGS"
        else:
            final_decision_label = "APPROVED"

        # Build Prominent Structured Evidence Section for LLM
        evidence_section = (
            "==================================================\n"
            "VALIDATION RESULTS (DETERMINISTIC AUTHORITATIVE EVIDENCE)\n"
            "==================================================\n"
            f"Deterministic Checks Status: {det_status}\n"
            f"Ruff Linter Status: {ruff_status}\n"
            f"Pytest Execution Status: {pytest_status}\n"
            f"Bandit Security Status: {bandit_status}\n"
            f"Authoritative Quality Gate: {authoritative_gate} ({final_decision_label})\n\n"
            "[DETERMINISTIC FAILURE & LOG DETAILS]\n"
            f"Ruff Output:\n{ruff_output[:1000]}\n\n"
            f"Pytest Output:\n{pytest_output[:1000]}\n\n"
            f"Bandit Output:\n{bandit_output[:1000]}\n"
            "=================================================="
        )

        # Include Tester's coverage analysis if available
        tester_section = ""
        if tester_analysis:
            tester_section = (
                "\n\n--- TESTER AGENT COVERAGE ANALYSIS ---\n"
                f"{tester_analysis[:1500]}\n"
            )

        code_section = self._extract_files_summary(generated_code)

        # A failed deterministic gate already contains the exact actionable
        # evidence. Do not ask an LLM to infer a qualitative review from a
        # failed or unavailable tool run: it can hallucinate issues and often
        # repeats the report, obscuring the real failure.
        if authoritative_gate == "FAIL":
            llm_review = (
                "### Review Summary\n"
                "The implementation was not approved because the deterministic quality gate failed. "
                "The findings below are limited to the recorded tool evidence.\n\n"
                f"### Correctness\nFAIL\n\n"
                f"### Quality Score\n40/100\n\n"
                f"### Final Status\n{final_decision_label}\n"
            )
        else:
            llm_review = await self._request_qualitative_review(
                system_prompt=(
                    "You are the Reviewer Agent in a multi-agent orchestration system.\n\n"
                    "Use only the supplied implementation and deterministic evidence. Do not invent "
                    "security vulnerabilities, files, tests, or requirements that are not present.\n\n"
                    "Provide one concise structured review containing Review Summary, Correctness, "
                    "Architecture, Security Findings, Code Quality, Test Result Assessment, "
                    "Quality Score out of 100, and Final Status."
                ),
                prompt=(
                    f"User Request:\n{user_request[:800]}\n\n"
                    f"Execution Plan:\n{execution_plan[:1500]}\n\n"
                    f"Research Notes:\n{research_notes[:800]}\n\n"
                    f"{evidence_section}\n\n{tester_section}\n\n{code_section}"
                ),
                authoritative_gate=authoritative_gate,
            )

        # Hard Python Enforcement: LLM text cannot override deterministic failure
        quality_gate = authoritative_gate
        raw_score = self._parse_quality_score(llm_review, quality_gate)
        if deterministic_failed:
            overall_score = min(raw_score, 40.0)  # Hard cap at 40.0 / 100 on validation failure
        else:
            overall_score = raw_score

        text_output = (
            f"{llm_review}\n\n"
            f"--- DETERMINISTIC QUALITY GATE EVIDENCE ---\n"
            f"Final Quality Gate: {quality_gate} ({final_decision_label})\n"
            f"Deterministic Checks: {det_status}\n"
            f"Ruff Status: {ruff_status}\n"
            f"Pytest Status: {pytest_status}\n"
            f"Bandit Status: {bandit_status}\n\n"
            f"Ruff Output:\n{ruff_output[:600]}\n\n"
            f"Test Output:\n{pytest_output[:600]}\n"
        )

        return {
            "output": text_output,
            "quality_gate": quality_gate,
            "overall_score": overall_score,
            "lint_findings": [{"tool": "ruff", "status": ruff_status, "output": ruff_output[:1000]}],
            "security_findings": [{"tool": "bandit", "status": bandit_status, "output": bandit_output[:1000]}],
        }

    async def _request_qualitative_review(
        self, system_prompt: str, prompt: str, authoritative_gate: str
    ) -> str:
        """Request a qualitative review only after deterministic validation passes."""
        try:
            return await self.client.chat(
                [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
                model=self.model,
                max_tokens=1000,
            )
        except Exception as exc:
            logger.error("Ollama request failed during review: %s – using fallback", exc)
            return f"[Fallback Reviewer] Validation Gate: {authoritative_gate}."

    def _extract_files_summary(self, generated_code: str, max_per_file: int = 1500) -> str:
        """Parse code blocks into per-file summaries for structured review."""
        pattern = r"```([a-zA-Z0-9_-]*)\s+(?:filepath|file)=[\"']?([^\"'\s\n>]+)[\"']?\n(.*?)```"
        matches = re.findall(pattern, generated_code, re.DOTALL)

        if not matches:
            # Fallback: no annotated blocks, show raw truncated
            return f"Generated Code (raw, no annotated file blocks found):\n{generated_code[:3000]}\n"

        sections: list[str] = []
        sections.append(f"**File Manifest** ({len(matches)} files generated):")
        for lang, path, _ in matches:
            sections.append(f"  - `{path}` ({lang or 'text'})")
        sections.append("")

        for lang, path, content in matches:
            lines = content.strip().splitlines()
            line_count = len(lines)
            truncated = content.strip()[:max_per_file]
            was_cut = len(content.strip()) > max_per_file
            sections.append(
                f"### File: `{path}` ({line_count} lines, {lang or 'text'})\n"
                f"```{lang or 'text'}\n{truncated}\n```"
                + ("\n*(truncated — file continues)*" if was_cut else "")
            )

        return "\n\n".join(sections)

    def _parse_quality_score(self, llm_review: str, quality_gate: str) -> float:
        """
        Parse the Quality Score from the LLM's review text.
        Falls back to gate-based defaults if no score is found.
        """
        # Try patterns like "Quality Score: 75/100", "Score: 80 / 100", "**Quality Score**: 65/100"
        patterns = [
            r"[Qq]uality\s*[Ss]core[:\s]*\**\s*(\d{1,3})\s*/\s*100",
            r"[Ss]core[:\s]*\**\s*(\d{1,3})\s*/\s*100",
            r"[Qq]uality\s*[Ss]core[:\s]*\**\s*(\d{1,3})",
            r"\*\*(\d{1,3})\s*/\s*100\*\*",
        ]
        for pattern in patterns:
            match = re.search(pattern, llm_review)
            if match:
                score = float(match.group(1))
                if 0 <= score <= 100:
                    return score

        # Fallback defaults based on quality gate
        if quality_gate == "FAIL":
            return 45.0
        elif quality_gate == "PASS_WITH_WARNINGS":
            return 72.0
        return 85.0
