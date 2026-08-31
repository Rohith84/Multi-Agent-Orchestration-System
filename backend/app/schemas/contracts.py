"""
Contract Schemas for Multi-Agent Orchestration.

Defines the deterministic data contracts between agents and the orchestrator.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator


class AgentType(str, Enum):
    """Explicit enum of allowed downstream LLM agents."""
    RESEARCH = "research"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"

    @classmethod
    def _missing_(cls, value: object) -> Any:
        # Handle common aliases (e.g. researcher -> research)
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ("researcher", "research"):
                return cls.RESEARCH
            if val in ("coder", "coding", "code", "developer"):
                return cls.CODER
            if val in ("tester", "testing", "test", "qa"):
                return cls.TESTER
            if val in ("reviewer", "review", "audit"):
                return cls.REVIEWER
        return super()._missing_(value)


class PlanSubtask(BaseModel):
    """A discrete, actionable subtask within a plan."""
    id: str | int = Field(..., description="Unique identifier for the subtask")
    agent: AgentType = Field(..., description="The specialized agent assigned to execute this subtask")
    description: str = Field(..., description="Concrete, non-empty description of what this subtask accomplishes")
    dependencies: list[str | int] = Field(default_factory=list, description="IDs of subtasks that must complete before this one")

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Subtask description cannot be empty")
        return v.strip()


class PlanContract(BaseModel):
    """
    Deterministic contract for a plan produced by the Planner Agent.
    Enforces strict structural and boundary invariants before any downstream execution.
    """
    task_summary: str = Field(..., description="One-line summary of the overall task")
    task_type: str = Field(default="coding", description="Type of task (coding, research, debugging, etc.)")
    complexity: str = Field(default="medium", description="Complexity estimate (low, medium, high)")
    required_agents: list[AgentType] = Field(..., description="List of agents required for this plan")
    subtasks: list[PlanSubtask] = Field(..., description="Ordered list of discrete subtasks (strictly 3 to 6)")
    execution_order: list[str | int] = Field(default_factory=list, description="Explicit subtask execution sequence")
    required_context: list[str] | str = Field(default="", description="Contextual prerequisites")
    required_tools: list[str] = Field(default_factory=list, description="Tools needed for execution")
    risks_or_unknowns: list[str] | str = Field(default="", description="Identified risks or ambiguities")
    file_manifest: list[str] = Field(default_factory=list, description="Target files to create or modify")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Acceptance criteria for task completion")

    @field_validator("task_summary")
    @classmethod
    def validate_summary(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Task summary cannot be empty")
        return v.strip()

    @model_validator(mode="after")
    def validate_plan_invariants(self) -> PlanContract:
        # 1. Subtask count bounds: strictly [3, 6]
        count = len(self.subtasks)
        if count < 3:
            raise ValueError(f"PlanContract violation: Minimum 3 subtasks required, got {count}")
        if count > 6:
            raise ValueError(f"PlanContract violation: Maximum 6 subtasks allowed, got {count}. Plan rejected.")

        # 2. Unique subtask IDs
        seen_ids = set()
        for st in self.subtasks:
            sid = str(st.id)
            if sid in seen_ids:
                raise ValueError(f"PlanContract violation: Duplicate subtask ID '{st.id}' found")
            seen_ids.add(sid)

        # 3. Duplicate subtasks detection (normalized descriptions)
        seen_descriptions = set()
        for st in self.subtasks:
            norm_desc = " ".join(st.description.lower().split())
            if norm_desc in seen_descriptions:
                raise ValueError(f"PlanContract violation: Duplicate subtask detected: '{st.description}'")
            seen_descriptions.add(norm_desc)

        # 4. Validate dependency references
        for st in self.subtasks:
            for dep in st.dependencies:
                dep_str = str(dep)
                if dep_str == str(st.id):
                    raise ValueError(f"PlanContract violation: Subtask '{st.id}' cannot depend on itself")
                if dep_str not in seen_ids:
                    raise ValueError(f"PlanContract violation: Subtask '{st.id}' references non-existent dependency '{dep}'")

        # 5. Validate execution_order references if provided
        if self.execution_order:
            for item in self.execution_order:
                item_str = str(item)
                if item_str not in seen_ids:
                    raise ValueError(f"PlanContract violation: execution_order references unknown subtask ID '{item}'")

        return self

    def to_markdown(self) -> str:
        """Render the validated plan as standardized markdown."""
        lines = [
            f"### Task Summary: {self.task_summary}",
            f"**Task Type**: {self.task_type}",
            f"**Complexity**: {self.complexity}",
            f"**Required Agents**: {', '.join(a.value for a in self.required_agents)}",
            "",
            "### Subtasks:",
        ]
        for st in self.subtasks:
            dep_text = f" (depends on: {', '.join(str(d) for d in st.dependencies)})" if st.dependencies else ""
            lines.append(f"{st.id}. **[{st.agent.value.upper()}]**: {st.description}{dep_text}")

        if self.file_manifest:
            lines.extend(["", "### File Manifest:"])
            for fm in self.file_manifest:
                lines.append(f"- `{fm}`")

        if self.acceptance_criteria:
            lines.extend(["", "### Acceptance Criteria:"])
            for ac in self.acceptance_criteria:
                lines.append(f"- {ac}")

        lines.extend(["", f"REQUIRED_AGENTS: {', '.join(a.value for a in self.required_agents)}"])
        return "\n".join(lines)
