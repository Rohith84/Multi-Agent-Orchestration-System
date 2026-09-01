"""
Reviewer Agent.
Performs evidence-bound qualitative architectural code review and enforces Quality Gate decisions.
Does NOT run linters or tests — consumes pre-computed validation_results from the Quality Gate.
Strictly evidence-bound:
- Prevents hallucination of lint/test/code errors on INFRASTRUCTURE_ERROR
- Preserves exact raw stdout/stderr/execution_error
- Differentiates OBSERVED FACTS from INFERENCES
- Reports CONTRACT_FAILURE with exact rules
- Reports RAG_SUCCESS, RAG_EMPTY, and RAG_INFRASTRUCTURE_ERROR accurately
- Marks missing structured evidence as UNAVAILABLE
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
    Reviewer Agent performs evidence-bound qualitative architectural review and enforces Quality Gate decisions.
    Consumes pre-computed validation_results from the Quality Gate without inventing unsupported defects.
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
        rag_result: dict[str, Any] | Any | None = None,
    ) -> dict[str, Any]:
        """
        Consumes Quality Gate evidence, evaluates LLM review against it, and returns QualityGate report.
        """
        logger.info("Executing Evidence-Bound Reviewer Agent with model=%s", self.model)

        # Normalize structured evidence without mutating raw outputs or inferring status from unstructured text
        normalized = self._normalize_evidence(
            validation_results, research_notes, tester_analysis, rag_result=rag_result
        )
        authoritative_gate = normalized["quality_gate"]
        final_decision_label = normalized["final_decision_label"]
        evidence_section = normalized["evidence_section"]

        tester_section = ""
        if tester_analysis:
            tester_section = f"\n\n--- TESTER AGENT COVERAGE ANALYSIS ---\n{tester_analysis[:1500]}\n"

        code_section = self._extract_files_summary(generated_code)

        # If Quality Gate explicitly failed, build actionable failure review based strictly on evidence
        deterministic_failed = authoritative_gate == "FAIL"
        if deterministic_failed:
            llm_review = (
                "### Review Summary\n"
                "The implementation was not approved because the deterministic quality gate failed. "
                "The findings below are strictly bound to the recorded tool and contract evidence.\n\n"
                "### Correctness\nFAIL\n\n"
                "### Quality Score\n40/100\n\n"
                f"### Final Status\n{final_decision_label}\n"
            )
        else:
            system_prompt = (
                "You are the Evidence-Bound Reviewer Agent in a multi-agent orchestration system.\n\n"
                "## Role & Responsibilities\n"
                "You perform qualitative architectural code review strictly grounded in deterministic tool evidence.\n\n"
                "## Critical Evidence Rules (MANDATORY)\n"
                "1. Deterministic tool results and Quality Gate decisions are authoritative for execution status.\n"
                "2. INFRASTRUCTURE_ERROR (e.g. FileNotFoundError, TimeoutExpired, tool process execution error) is an infrastructure failure, NOT a code defect, lint error, or test failure. If a tool has status INFRASTRUCTURE_ERROR, state clearly that tool execution failed due to an infrastructure error and code quality cannot be evaluated from this evidence. NEVER claim linter found errors or tests failed when tool execution failed.\n"
                "3. Distinguish OBSERVED FACTS (actual output in tool evidence) from INFERENCES (speculation). Never present inferences as confirmed facts.\n"
                "4. For CodeContract CONTRACT_FAILURE, reference only the actual recorded contract violations (missing manifest files, syntax errors, empty files, placeholders, pass stubs). Do not invent additional violations.\n"
                "5. For RAG evidence:\n"
                "   - RAG_INFRASTRUCTURE_ERROR means Knowledge Base retrieval failed. Never state 'no documents were found'.\n"
                "   - RAG_EMPTY means retrieval succeeded but returned 0 documents.\n"
                "   - RAG_SUCCESS means retrieved documents are available with citations.\n"
                "6. If evidence is marked UNAVAILABLE, explicitly state that evidence is unavailable rather than assuming PASS or FAIL.\n"
                "7. Do not claim broader guarantees than the evidence supports (e.g. do not claim code is 'Production-ready' unless checks explicitly verify it).\n\n"
                "## Output Format\n"
                "Provide one concise structured review containing:\n"
                "- **Review Summary**: Concise evidence-bound summary.\n"
                "- **Correctness**: Evidence-bound assessment.\n"
                "- **Architecture**: Component structure and design patterns.\n"
                "- **Security Findings**: Evidence-bound security assessment.\n"
                "- **Code Quality**: Readability, maintainability, and standards.\n"
                "- **Test Result Assessment**: Based strictly on test output.\n"
                "- **Quality Score**: Score out of 100.\n"
                "- **Final Status**: APPROVED / APPROVED_WITH_WARNINGS / REJECTED.\n"
            )

            prompt = (
                f"User Request:\n{user_request[:800]}\n\n"
                f"Execution Plan:\n{execution_plan[:1500]}\n\n"
                f"Research Notes:\n{research_notes[:800]}\n\n"
                f"{evidence_section}\n\n{tester_section}\n\n{code_section}"
            )

            llm_review = await self._request_qualitative_review(
                system_prompt=system_prompt,
                prompt=prompt,
                authoritative_gate=authoritative_gate,
            )

        quality_gate = authoritative_gate
        raw_score = self._parse_quality_score(llm_review, quality_gate)
        overall_score = min(raw_score, 40.0) if deterministic_failed else raw_score

        text_output = (
            f"{llm_review}\n\n"
            f"--- DETERMINISTIC EVIDENCE SUMMARY ---\n"
            f"Final Quality Gate: {quality_gate} ({final_decision_label})\n"
            f"{evidence_section[:1500]}\n"
        )

        return {
            "output": text_output,
            "quality_gate": quality_gate,
            "overall_score": overall_score,
            "lint_findings": normalized.get("lint_findings", []),
            "security_findings": normalized.get("security_findings", []),
        }

    def _normalize_evidence(
        self,
        validation_results: dict[str, Any] | None,
        research_notes: str = "",
        tester_analysis: str = "",
        rag_result: dict[str, Any] | Any | None = None,
    ) -> dict[str, Any]:
        """
        Normalize evidence deterministically for Reviewer context without mutating raw outputs or fabricating statuses.
        Uses structured rag_result as authoritative over research_notes prose when present.
        """
        if not validation_results:
            gate = "FAIL"
            decision_label = "REJECTED"
            evidence_text = (
                "==================================================\n"
                "VALIDATION RESULTS (MISSING EVIDENCE)\n"
                "==================================================\n"
                "Quality Gate Status: FAIL (Missing Evidence)\n"
                "CodeContract Status: UNAVAILABLE\n"
                "Ruff Linter Status: UNAVAILABLE\n"
                "Pytest Execution Status: UNAVAILABLE\n"
                "Bandit Security Status: UNAVAILABLE\n"
                "Note: No validation results were provided.\n"
                "=================================================="
            )
            return {
                "quality_gate": gate,
                "final_decision_label": decision_label,
                "evidence_section": evidence_text,
                "lint_findings": [],
                "security_findings": [],
            }

        gate = validation_results.get("quality_gate", "FAIL")
        if gate == "FAIL":
            decision_label = "REJECTED"
        elif gate == "PASS_WITH_WARNINGS":
            decision_label = "APPROVED_WITH_WARNINGS"
        else:
            decision_label = "APPROVED"

        lines = [
            "==================================================",
            "VALIDATION RESULTS (DETERMINISTIC AUTHORITATIVE EVIDENCE)",
            "==================================================",
            f"Authoritative Quality Gate: {gate} ({decision_label})",
        ]

        # 1. CodeContract Evidence
        code_contract = validation_results.get("code_contract")
        if isinstance(code_contract, dict):
            cc_status = code_contract.get("status", "UNAVAILABLE")
            cc_summary = code_contract.get("summary", "")
            lines.append(f"CodeContract Status: {cc_status}")
            if cc_status == "CONTRACT_FAILURE":
                lines.append(f"CodeContract Violations: {cc_summary}")
                errors = code_contract.get("errors", [])
                for err in errors:
                    lines.append(f"  - [{err.get('rule')}] {err.get('file')}:{err.get('line') or 1}: {err.get('message')}")
        else:
            lines.append("CodeContract Status: UNAVAILABLE")

        # 2. Tool Evidence Helper
        lint_findings = []
        security_findings = []

        def process_tool(tool_key: str, display_name: str) -> tuple[str, str, str]:
            tool_entry = validation_results.get(tool_key)
            if not isinstance(tool_entry, dict):
                return "UNAVAILABLE", "No evidence provided for this tool.", ""

            # Check if structured result dict exists
            res_dict = tool_entry.get("result")
            status = tool_entry.get("status")
            output = tool_entry.get("output", "")

            if isinstance(res_dict, dict):
                structured_status = res_dict.get("status")
                exit_code = res_dict.get("exit_code")
                stdout = res_dict.get("stdout", "")
                stderr = res_dict.get("stderr", "")
                exec_err = res_dict.get("execution_error")

                if structured_status == "INFRASTRUCTURE_ERROR":
                    status_str = "INFRASTRUCTURE_ERROR"
                    detail = (
                        f"[INFRASTRUCTURE ERROR] Tool execution failed due to an infrastructure error ({exec_err or 'process error'}). "
                        "Code quality or defects cannot be evaluated from this tool."
                    )
                elif structured_status == "LINT_FAILURE":
                    status_str = "LINT_FAILURE"
                    detail = f"[LINT FAILURE] Exit Code {exit_code}\nstdout:\n{stdout}\nstderr:\n{stderr}"
                elif structured_status == "TEST_FAILURE":
                    status_str = "TEST_FAILURE"
                    detail = f"[TEST FAILURE] Exit Code {exit_code}\nstdout:\n{stdout}\nstderr:\n{stderr}"
                elif structured_status == "CONFIG_ERROR":
                    status_str = "CONFIG_ERROR"
                    detail = f"[CONFIG ERROR] Exit Code {exit_code}\nstderr:\n{stderr}\nstdout:\n{stdout}"
                elif structured_status == "PASS":
                    status_str = "PASS"
                    detail = f"[PASS] Exit Code 0\nstdout:\n{stdout}"
                else:
                    status_str = str(structured_status)
                    detail = f"stdout:\n{stdout}\nstderr:\n{stderr}"
                return status_str, detail, stdout or stderr or output
            else:
                # Unstructured / String fallback: do NOT infer INFRASTRUCTURE_ERROR from raw string unless status field is set
                if status is not None:
                    status_str = str(status)
                else:
                    status_str = "UNAVAILABLE"
                return status_str, output, output

        # Ruff
        ruff_st, ruff_detail, ruff_raw = process_tool("ruff", "Ruff")
        lines.append(f"Ruff Linter Status: {ruff_st}")
        lines.append(f"Ruff Evidence Detail:\n{ruff_detail[:800]}\n")
        lint_findings.append({"tool": "ruff", "status": ruff_st, "output": ruff_raw[:1000]})

        # Pytest
        pytest_st, pytest_detail, pytest_raw = process_tool("pytest", "Pytest")
        lines.append(f"Pytest Execution Status: {pytest_st}")
        lines.append(f"Pytest Evidence Detail:\n{pytest_detail[:800]}\n")

        # Bandit
        bandit_st, bandit_detail, bandit_raw = process_tool("bandit", "Bandit")
        lines.append(f"Bandit Security Status: {bandit_st}")
        lines.append(f"Bandit Evidence Detail:\n{bandit_detail[:800]}\n")
        security_findings.append({"tool": "bandit", "status": bandit_st, "output": bandit_raw[:1000]})

        # 3. RAG Status Normalization: Structured rag_result takes absolute precedence over research_notes prose
        if rag_result is not None:
            if isinstance(rag_result, dict):
                st_val = rag_result.get("status")
                err_msg = rag_result.get("error")
                chunks = rag_result.get("chunks", [])
            else:
                st_val = getattr(rag_result, "status", None)
                err_msg = getattr(rag_result, "error", None)
                chunks = getattr(rag_result, "chunks", [])

            st_val_str = st_val.value if hasattr(st_val, "value") else str(st_val)

            if st_val_str == "RAG_INFRASTRUCTURE_ERROR":
                lines.append(f"RAG Status: RAG_INFRASTRUCTURE_ERROR (Knowledge Base retrieval failed: {err_msg or 'Infrastructure error'}. Context unavailable. Do NOT claim no documents exist.)")
            elif st_val_str == "RAG_EMPTY":
                lines.append("RAG Status: RAG_EMPTY (Knowledge Base accessed successfully, 0 matching documents found.)")
            elif st_val_str == "RAG_SUCCESS":
                lines.append(f"RAG Status: RAG_SUCCESS (Relevant Knowledge Base documents retrieved: {len(chunks)} chunk(s) available.)")
            else:
                lines.append(f"RAG Status: {st_val_str}")
        else:
            # Fallback to prose parsing ONLY if rag_result is completely absent
            if "Status: RAG_INFRASTRUCTURE_ERROR" in research_notes or "ERROR: Knowledge Base retrieval failed due to an infrastructure error" in research_notes:
                lines.append("RAG Status: RAG_INFRASTRUCTURE_ERROR (Knowledge Base retrieval failed due to infrastructure error. Context unavailable. Do NOT claim no documents exist.)")
            elif "Status: RAG_EMPTY" in research_notes or "returned 0 relevant document chunks" in research_notes:
                lines.append("RAG Status: RAG_EMPTY (Knowledge Base accessed successfully, 0 matching documents found.)")
            elif "Status: RAG_SUCCESS" in research_notes or "RETRIEVED DOCUMENTS & KNOWLEDGE" in research_notes:
                lines.append("RAG Status: RAG_SUCCESS (Relevant Knowledge Base documents retrieved.)")
            else:
                lines.append("RAG Status: UNAVAILABLE (No explicit RAG status found in research notes)")

        lines.append("================================")

        return {
            "quality_gate": gate,
            "final_decision_label": decision_label,
            "evidence_section": "\n".join(lines),
            "lint_findings": lint_findings,
            "security_findings": security_findings,
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

        if quality_gate == "FAIL":
            return 45.0
        elif quality_gate == "PASS_WITH_WARNINGS":
            return 72.0
        return 85.0
