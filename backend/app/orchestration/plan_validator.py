"""
Deterministic Plan Contract Validator.

Enforces structural and boundary invariants on execution plans before
any downstream orchestrator execution begins.
"""

from __future__ import annotations

import re
from typing import Any
from pydantic import ValidationError

from app.core.logging import get_logger
from app.schemas.contracts import PlanContract, PlanSubtask, AgentType

logger = get_logger(__name__)


class PlanContractValidationError(Exception):
    """Exception raised when a plan violates the deterministic Plan Contract."""
    def __init__(self, message: str, errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.errors = errors or [message]


class PlanValidationResult:
    """Result of plan contract validation."""
    def __init__(
        self,
        is_valid: bool,
        contract: PlanContract | None = None,
        errors: list[str] | None = None,
    ) -> None:
        self.is_valid = is_valid
        self.contract = contract
        self.errors = errors or []

    def __bool__(self) -> bool:
        return self.is_valid

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "contract": self.contract.model_dump() if self.contract else None,
            "errors": self.errors,
        }


class PlanContractValidator:
    """
    Deterministic validator for execution plans.

    Guarantees:
    - Plans with <3 or >6 subtasks are rejected immediately.
    - Repetitive loops (e.g. 500 or 577 duplicate steps) are rejected.
    - Plans are NEVER silently truncated or coerced.
    - Invalid plans cannot proceed to downstream agent execution.
    """

    @classmethod
    def validate(cls, plan_input: PlanContract | dict[str, Any] | str) -> PlanValidationResult:
        """
        Validate a PlanContract instance, a dictionary, or raw markdown plan text.
        Returns a PlanValidationResult with is_valid=True and the validated PlanContract,
        or is_valid=False with detailed rejection reasons.
        """
        if isinstance(plan_input, PlanContract):
            return PlanValidationResult(is_valid=True, contract=plan_input)

        if isinstance(plan_input, dict):
            try:
                contract = PlanContract(**plan_input)
                return PlanValidationResult(is_valid=True, contract=contract)
            except ValidationError as ve:
                err_msgs = [e["msg"] for e in ve.errors()]
                logger.warning("PlanContract validation failed: %s", err_msgs)
                return PlanValidationResult(is_valid=False, errors=err_msgs)
            except Exception as e:
                logger.warning("PlanContract validation failed: %s", e)
                return PlanValidationResult(is_valid=False, errors=[str(e)])

        if isinstance(plan_input, str):
            text = plan_input.strip()
            if not text:
                return PlanValidationResult(is_valid=False, errors=["Plan text is empty."])

            # Try parsing as JSON first (direct or embedded in ```json ... ```)
            json_str = None
            if text.startswith("{") and text.endswith("}"):
                json_str = text
            else:
                json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
                if json_block_match:
                    json_str = json_block_match.group(1).strip()
                elif "{" in text and "}" in text:
                    # Attempt to isolate outermost JSON object
                    start_idx = text.find("{")
                    end_idx = text.rfind("}")
                    if start_idx != -1 and end_idx > start_idx:
                        json_str = text[start_idx : end_idx + 1].strip()

            if json_str:
                import json
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict):
                        return cls.validate(data)
                except json.JSONDecodeError as jde:
                    logger.debug("Failed to parse JSON plan: %s", jde)
                    # If JSON was explicitly formatted but malformed, record error
                    if text.startswith("{") or "```json" in text:
                        return PlanValidationResult(is_valid=False, errors=[f"Malformed JSON plan: {jde}"])

            # Fall back to strict markdown parsing
            try:
                contract = cls.parse_markdown_plan(text)
                return PlanValidationResult(is_valid=True, contract=contract)
            except PlanContractValidationError as pe:
                return PlanValidationResult(is_valid=False, errors=pe.errors)
            except Exception as e:
                return PlanValidationResult(is_valid=False, errors=[str(e)])

        return PlanValidationResult(
            is_valid=False,
            errors=[f"Unsupported plan input type: {type(plan_input).__name__}"],
        )

    @classmethod
    def validate_or_raise(cls, plan_input: PlanContract | dict[str, Any] | str) -> PlanContract:
        """
        Validate plan and return the validated PlanContract, or raise PlanContractValidationError.
        """
        res = cls.validate(plan_input)
        if not res.is_valid or res.contract is None:
            err_summary = "; ".join(res.errors)
            raise PlanContractValidationError(f"Plan Contract Violation: {err_summary}", errors=res.errors)
        return res.contract

    @classmethod
    def parse_markdown_plan(cls, raw_text: str) -> PlanContract:
        """
        Parse raw markdown text output from the Planner Agent into a structured PlanContract.
        Applies strict validation to guarantee no unvalidated text slips through.
        """
        if not raw_text or not raw_text.strip():
            raise PlanContractValidationError("Plan text is empty.")

        text = raw_text.strip()

        # 1. Extract Task Summary
        task_summary_match = re.search(r"\*\*Task Summary\*\*:\s*([^\n]+)", text, re.IGNORECASE)
        if not task_summary_match:
            task_summary_match = re.search(r"### Task Summary:?\s*([^\n]+)", text, re.IGNORECASE)
        task_summary = task_summary_match.group(1).strip() if task_summary_match else "Task Execution Plan"

        # 2. Extract Task Type
        task_type_match = re.search(r"\*\*Task Type\*\*:\s*([^\n]+)", text, re.IGNORECASE)
        task_type = task_type_match.group(1).strip().lower() if task_type_match else "coding"

        # 3. Extract Complexity
        complexity_match = re.search(r"\*\*Complexity\*\*:\s*([^\n]+)", text, re.IGNORECASE)
        complexity = complexity_match.group(1).strip().lower() if complexity_match else "medium"

        # 4. Extract Required Agents
        req_agents_match = re.search(r"REQUIRED_AGENTS:\s*([^\n]+)", text, re.IGNORECASE)
        if not req_agents_match:
            req_agents_match = re.search(r"\*\*Required Agents\*\*:\s*([^\n]+)", text, re.IGNORECASE)

        required_agents = []
        if req_agents_match:
            raw_agents = req_agents_match.group(1).replace(",", " ").split()
            for a in raw_agents:
                try:
                    required_agents.append(AgentType(a))
                except (ValueError, KeyError):
                    pass

        if not required_agents:
            required_agents = [AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER, AgentType.REVIEWER]

        # 5. Extract Subtasks
        subtasks: list[PlanSubtask] = []
        subtask_section = ""
        
        # Locate Subtasks section
        subtasks_hdr = re.search(r"\*\*Subtasks\*\*:?(.*?)(?:\*\*Execution Order\*\*|\*\*Required Context\*\*|###|\Z)", text, re.DOTALL | re.IGNORECASE)
        if not subtasks_hdr:
            subtasks_hdr = re.search(r"### Subtasks:?(.*?)(?:###|\Z)", text, re.DOTALL | re.IGNORECASE)

        if subtasks_hdr:
            subtask_section = subtasks_hdr.group(1).strip()

        # Parse numbered list items: "1. **Research**: Description" or "1. Description"
        pattern = re.compile(r"^\s*(\d+)[\.\)]\s*(?:\*\*([^*]+)\*\*:?)?\s*(.*)$", re.MULTILINE)
        matches = list(pattern.finditer(subtask_section))

        # Check total raw count — if LLM generated 577 steps or >6 steps, do not truncate; reject!
        if len(matches) > 6:
            raise PlanContractValidationError(
                f"PlanContract violation: Planner generated {len(matches)} subtasks (strictly maximum 6 allowed). Plan rejected."
            )

        for match in matches:
            step_id = match.group(1).strip()
            agent_or_label = (match.group(2) or "").strip().lower()
            desc = match.group(3).strip()

            # If description is empty but label had the text
            if not desc and agent_or_label:
                desc = agent_or_label
                agent_or_label = ""

            # Determine agent
            assigned_agent = AgentType.CODER  # default
            if "research" in agent_or_label or "research" in desc.lower():
                assigned_agent = AgentType.RESEARCH
            elif "test" in agent_or_label or "test" in desc.lower():
                assigned_agent = AgentType.TESTER
            elif "review" in agent_or_label or "review" in desc.lower():
                assigned_agent = AgentType.REVIEWER
            elif "coder" in agent_or_label or "code" in agent_or_label:
                assigned_agent = AgentType.CODER

            subtasks.append(
                PlanSubtask(
                    id=step_id,
                    agent=assigned_agent,
                    description=f"{agent_or_label}: {desc}".strip(": ") if agent_or_label else desc,
                    dependencies=[],
                )
            )

        # 6. Extract File Manifest
        file_manifest = []
        manifest_match = re.search(r"\*\*File Manifest\*\*:?(.*?)(?:\*\*Database Design\*\*|\*\*API Specification\*\*|\*\*Acceptance Criteria\*\*|###|\Z)", text, re.DOTALL | re.IGNORECASE)
        if manifest_match:
            lines = manifest_match.group(1).strip().splitlines()
            for line in lines:
                file_match = re.search(r"`([^`]+)`", line)
                if file_match:
                    file_manifest.append(file_match.group(1).strip())

        # Construct and validate PlanContract
        try:
            return PlanContract(
                task_summary=task_summary,
                task_type=task_type,
                complexity=complexity,
                required_agents=required_agents,
                subtasks=subtasks,
                file_manifest=file_manifest,
            )
        except ValidationError as ve:
            err_msgs = [e["msg"] for e in ve.errors()]
            raise PlanContractValidationError(f"Plan Contract Violation: {'; '.join(err_msgs)}", errors=err_msgs)
        except Exception as e:
            raise PlanContractValidationError(f"Plan Contract Violation: {e}", errors=[str(e)])
