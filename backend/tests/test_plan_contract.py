"""
Tests for Phase 1: Deterministic Plan Contract Validator.

Validates that:
- Plans strictly enforce [3, 6] subtask bounds.
- 577-step, 7-step, and 2-step runaway or deficient plans are rejected.
- Duplicate IDs, duplicate subtasks, invalid agents, and invalid dependencies are rejected.
- Plans are NEVER silently truncated or executed when malformed.
"""

import pytest
from pydantic import ValidationError

from app.schemas.contracts import PlanContract, PlanSubtask, AgentType
from app.orchestration.plan_validator import (
    PlanContractValidator,
    PlanContractValidationError,
)


def test_valid_3_task_plan():
    """Verify that a valid plan with 3 subtasks passes validation."""
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Research requirements", dependencies=[]),
        PlanSubtask(id=2, agent=AgentType.CODER, description="Implement calculator CLI", dependencies=[1]),
        PlanSubtask(id=3, agent=AgentType.TESTER, description="Run pytest suite", dependencies=[2]),
    ]
    contract = PlanContract(
        task_summary="Build Python CLI Calculator",
        task_type="coding",
        complexity="low",
        required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER],
        subtasks=subtasks,
        execution_order=[1, 2, 3],
        file_manifest=["calculator.py", "test_calculator.py"],
    )

    res = PlanContractValidator.validate(contract)
    assert res.is_valid is True
    assert res.contract is not None
    assert len(res.contract.subtasks) == 3


def test_valid_6_task_plan():
    """Verify that a valid plan with maximum allowable (6) subtasks passes validation."""
    subtasks = [
        PlanSubtask(id="1", agent=AgentType.RESEARCH, description="Analyze CLI parsing options", dependencies=[]),
        PlanSubtask(id="2", agent=AgentType.RESEARCH, description="Document arithmetic specs", dependencies=["1"]),
        PlanSubtask(id="3", agent=AgentType.CODER, description="Write core calculator arithmetic functions", dependencies=["2"]),
        PlanSubtask(id="4", agent=AgentType.CODER, description="Create Click CLI entry point", dependencies=["3"]),
        PlanSubtask(id="5", agent=AgentType.TESTER, description="Write parameterized unit tests", dependencies=["4"]),
        PlanSubtask(id="6", agent=AgentType.REVIEWER, description="Audit code architecture and test evidence", dependencies=["5"]),
    ]
    contract = PlanContract(
        task_summary="Implement Enterprise Calculator",
        task_type="coding",
        complexity="medium",
        required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER, AgentType.REVIEWER],
        subtasks=subtasks,
        execution_order=["1", "2", "3", "4", "5", "6"],
    )

    res = PlanContractValidator.validate(contract)
    assert res.is_valid is True
    assert len(res.contract.subtasks) == 6


def test_2_task_plan_rejected():
    """Verify that a deficient plan (< 3 subtasks) is rejected."""
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Research specs"),
        PlanSubtask(id=2, agent=AgentType.CODER, description="Write code"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Too short plan",
            required_agents=[AgentType.RESEARCH, AgentType.CODER],
            subtasks=subtasks,
        )
    assert "Minimum 3 subtasks required" in str(exc_info.value)


def test_7_task_plan_rejected():
    """Verify that a plan exceeding 6 subtasks is rejected."""
    subtasks = [
        PlanSubtask(id=i, agent=AgentType.CODER, description=f"Task step {i}")
        for i in range(1, 8)
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Overlong plan",
            required_agents=[AgentType.CODER],
            subtasks=subtasks,
        )
    assert "Maximum 6 subtasks allowed" in str(exc_info.value)


def test_577_task_runaway_plan_rejected():
    """Verify that a 577-step hallucinated runaway plan is rejected deterministically."""
    subtasks = [
        PlanSubtask(id=i, agent=AgentType.CODER, description=f"Subtask number {i} execution step")
        for i in range(1, 578)
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Runaway hallucinated plan",
            required_agents=[AgentType.CODER],
            subtasks=subtasks,
        )
    assert "Maximum 6 subtasks allowed, got 577" in str(exc_info.value)


def test_markdown_parser_rejects_577_steps():
    """Verify that the markdown parser rejects a raw text containing 577 steps without silently truncating."""
    lines = ["**Task Summary**: Build runaway calculator", "**Subtasks**:"]
    for i in range(1, 578):
        lines.append(f"{i}. **Coder**: Implement part {i}")

    raw_markdown = "\n".join(lines)

    with pytest.raises(PlanContractValidationError) as exc_info:
        PlanContractValidator.parse_markdown_plan(raw_markdown)

    assert "strictly maximum 6 allowed" in str(exc_info.value)
    assert "Plan rejected" in str(exc_info.value)


def test_duplicate_subtask_ids_rejected():
    """Verify that duplicate subtask IDs are rejected."""
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Step A"),
        PlanSubtask(id=1, agent=AgentType.CODER, description="Step B"),
        PlanSubtask(id=2, agent=AgentType.TESTER, description="Step C"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Duplicate IDs plan",
            required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER],
            subtasks=subtasks,
        )
    assert "Duplicate subtask ID '1' found" in str(exc_info.value)


def test_duplicate_subtasks_rejected():
    """Verify that duplicate subtasks (same description) are rejected."""
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Understand CLI development and arithmetic"),
        PlanSubtask(id=2, agent=AgentType.RESEARCH, description="understand cli development and arithmetic"),  # Normalized duplicate
        PlanSubtask(id=3, agent=AgentType.TESTER, description="Write tests"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Duplicate subtasks plan",
            required_agents=[AgentType.RESEARCH, AgentType.TESTER],
            subtasks=subtasks,
        )
    assert "Duplicate subtask detected" in str(exc_info.value)


def test_invalid_agent_rejected():
    """Verify that unknown agent types are rejected."""
    with pytest.raises(ValidationError):
        PlanSubtask(
            id=1,
            agent="hacker_agent",  # type: ignore
            description="Run arbitrary unauthorized actions",
        )


def test_invalid_dependency_rejected():
    """Verify that referencing a non-existent dependency is rejected."""
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Research specs"),
        PlanSubtask(id=2, agent=AgentType.CODER, description="Write code", dependencies=[99]),  # Non-existent 99
        PlanSubtask(id=3, agent=AgentType.TESTER, description="Write tests", dependencies=[2]),
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Broken dependency plan",
            required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER],
            subtasks=subtasks,
        )
    assert "references non-existent dependency '99'" in str(exc_info.value)


def test_self_dependency_rejected():
    """Verify that a subtask cannot depend on itself."""
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Research specs"),
        PlanSubtask(id=2, agent=AgentType.CODER, description="Write code", dependencies=[2]),  # Self-dependency
        PlanSubtask(id=3, agent=AgentType.TESTER, description="Write tests", dependencies=[2]),
    ]
    with pytest.raises(ValidationError) as exc_info:
        PlanContract(
            task_summary="Self dependency plan",
            required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER],
            subtasks=subtasks,
        )
    assert "cannot depend on itself" in str(exc_info.value)
