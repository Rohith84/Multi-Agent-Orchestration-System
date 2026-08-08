"""
Pydantic schemas for Workflows, Checkpoints, Approvals, Schedules, and Planning Memory endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStartRequest(BaseModel):
    """Request to start or create a workflow."""

    message: str = Field(..., min_length=1, description="User request for the workflow.")
    session_id: str | None = Field(default=None, description="Optional chat session ID.")
    title: str | None = Field(default=None, description="Optional title for the workflow.")
    require_approval_agents: list[str] = Field(
        default_factory=list,
        description="List of agent names that require human approval before execution (e.g. ['coder', 'tester']).",
    )


class WorkflowApprovalDecision(BaseModel):
    """Request to approve or reject a paused workflow stage."""

    comments: str | None = Field(default=None, description="Optional approval or rejection notes.")


class WorkflowScheduleRequest(BaseModel):
    """Request to schedule a recurring or future workflow execution."""

    title: str = Field(..., min_length=1, description="Schedule title.")
    message: str = Field(..., min_length=1, description="Workflow goal or prompt.")
    cron_expression: str = Field(default="0 0 * * *", description="Cron pattern (e.g. '0 0 * * *') or interval string ('interval:60').")
    require_approval_agents: list[str] = Field(default_factory=list, description="Agent approval requirements.")


from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _stringify_uuid(v: Any) -> Any:
    if isinstance(v, UUID):
        return str(v)
    return v


class WorkflowCheckpointSchema(BaseModel):
    """Schema representing a single workflow checkpoint snapshot."""

    id: str
    workflow_id: str
    agent_name: str
    shared_state: dict[str, Any]
    tool_history: list[dict[str, Any]]
    research_context: str
    chat_context: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "workflow_id", mode="before")
    @classmethod
    def convert_uuid(cls, v: Any) -> Any:
        return _stringify_uuid(v)


class WorkflowApprovalSchema(BaseModel):
    """Schema representing a human approval gate request."""

    id: str
    workflow_id: str
    agent_name: str
    status: str
    comments: str | None
    requested_at: datetime
    decided_at: datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "workflow_id", mode="before")
    @classmethod
    def convert_uuid(cls, v: Any) -> Any:
        return _stringify_uuid(v)


class WorkflowSchema(BaseModel):
    """Schema representing a complete workflow instance."""

    id: str
    session_id: str
    title: str
    user_request: str
    status: str
    current_agent: str
    progress_percentage: int
    require_approval_agents: list[str]
    execution_time: float
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("id", "session_id", mode="before")
    @classmethod
    def convert_uuid(cls, v: Any) -> Any:
        return _stringify_uuid(v)


class WorkflowDetailSchema(WorkflowSchema):
    """Detailed workflow view containing history, checkpoints, and approvals."""

    checkpoints: list[WorkflowCheckpointSchema] = Field(default_factory=list)
    approvals: list[WorkflowApprovalSchema] = Field(default_factory=list)


class WorkflowListResponse(BaseModel):
    """Response containing a list of workflows."""

    workflows: list[WorkflowSchema]
    total: int


class WorkflowScheduleSchema(BaseModel):
    """Schema for a workflow schedule rule."""

    id: UUID | str
    title: str
    user_request: str
    cron_expression: str
    require_approval_agents: list[str]
    status: str
    last_run_at: datetime | None
    next_run_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowScheduleListResponse(BaseModel):
    """Response containing workflow schedules."""

    schedules: list[WorkflowScheduleSchema]
    total: int


class PlanningMemorySchema(BaseModel):
    """Schema for a saved planning memory."""

    id: str
    goal: str
    plan: str
    success_score: float
    execution_time: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
