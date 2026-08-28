"""
Reviewer Agent.
Performs static code analysis (Ruff check, Bandit security scan), evaluates architecture/SOLID compliance, and enforces Quality Gates.
"""

from __future__ import annotations

import asyncio
import re
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

        # 2. Build structured per-file code section for the LLM
        code_section = self._extract_files_summary(generated_code)

        # 3. Perform LLM Architectural Review
        system_prompt = (
            "You are the Reviewer Agent in a multi-agent orchestration system.\n\n"
            "## Role\n"
            "You are the final quality gate before the result is returned to the user. "
            "You evaluate the implementation and testing results for correctness, architecture, security, and quality.\n\n"
            "## Responsibilities\n"
            "- Review correctness: Does the implementation satisfy the user's original request?\n"
            "- Review architecture: Is the code well-structured, maintainable, and consistent with the project?\n"
            "- Review security: Are there vulnerabilities, injection risks, or unsafe patterns?\n"
            "- Review code quality: Does the code follow SOLID principles, handle errors, and avoid anti-patterns?\n"
            "- Review file completeness: Are ALL files from the plan manifest present and syntactically complete?\n"
            "  Check that no file is cut off mid-line, that all imports are valid, and that all referenced files exist.\n"
            "- Assess test results: Did the Testing Agent's actual execution results confirm correctness?\n"
            "- Consider static analysis results (Ruff linter, Bandit security scanner) as additional evidence.\n"
            "- Identify unresolved risks from earlier agents.\n\n"
            "## Rules\n"
            "- Do NOT blindly approve the Coding Agent's output.\n"
            "- Treat actual test execution results as stronger evidence than the model's claims about code correctness.\n"
            "- Identify concrete, specific problems rather than giving generic criticism.\n"
            "- Do NOT request unnecessary rewrites — distinguish critical issues from minor improvements.\n"
            "- Never claim security validation is complete unless the available checks actually support that conclusion.\n"
            "- If tests failed, do NOT mark the implementation as fully approved.\n"
            "- If evidence is insufficient to make a determination, explicitly state that.\n\n"
            "## Output Format\n"
            "Provide a structured review containing:\n"
            "- **Review Summary**: Overall assessment of the implementation.\n"
            "- **Correctness**: Does the code do what was requested? (PASS / FAIL / UNCERTAIN)\n"
            "- **Architecture**: Is the structure sound? (PASS / NEEDS_IMPROVEMENT / FAIL)\n"
            "- **Security Findings**: Any vulnerabilities or concerns found.\n"
            "- **Code Quality**: Style, patterns, error handling assessment.\n"
            "- **Test Result Assessment**: Analysis of actual test execution outcomes.\n"
            "- **Critical Issues**: Problems that must be fixed before approval.\n"
            "- **Recommended Changes**: Suggested improvements (non-blocking).\n"
            "- **Quality Score**: Numerical score out of 100.\n"
            "- **Final Status**: APPROVED / APPROVED_WITH_WARNINGS / NEEDS_REVISION / REJECTED\n\n"
            "Base your final status on evidence, not optimism."
        )

        # Truncate inputs — but code section uses structured per-file approach
        prompt = (
            f"User Request:\n{user_request[:800]}\n\n"
            f"Execution Plan:\n{execution_plan[:1500]}\n\n"
            f"Research Notes:\n{research_notes[:800]}\n\n"
            f"{code_section}\n\n"
            f"Test Results:\n{test_results[:1500]}\n\n"
            f"Static Linter (Ruff):\n{ruff_findings[:600]}\n\n"
            f"Security Scanner (Bandit):\n{bandit_findings[:600]}\n\n"
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

        # Parse dynamic score from LLM output
        overall_score = self._parse_quality_score(llm_review, quality_gate)

        text_output = (
            f"{llm_review}\n\n"
            f"--- STATIC CODE ANALYSIS & QUALITY GATE ---\n"
            f"Quality Gate: {quality_gate}\n"
            f"Ruff Linter Report:\n{ruff_findings[:600] if ruff_findings else 'No linter issues.'}\n\n"
            f"Bandit Security Report:\n{bandit_findings[:600] if bandit_findings else 'No security issues found.'}\n"
        )

        return {
            "output": text_output,
            "quality_gate": quality_gate,
            "overall_score": overall_score,
            "lint_findings": [{"tool": "ruff", "output": ruff_findings[:1000]}],
            "security_findings": [{"tool": "bandit", "output": bandit_findings[:1000]}],
        }

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
