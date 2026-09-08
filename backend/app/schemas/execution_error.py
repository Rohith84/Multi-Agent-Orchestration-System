"""
Pydantic schemas for Structured Execution Errors and Workflow Statuses.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionErrorType(str, Enum):
    """Classification of runtime/execution failures."""

    AGENT_FAILURE = "AGENT_FAILURE"
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    TOOL_FAILURE = "TOOL_FAILURE"
    TOOL_TIMEOUT = "TOOL_TIMEOUT"
    WORKSPACE_FAILURE = "WORKSPACE_FAILURE"
    GRAPH_FAILURE = "GRAPH_FAILURE"
    CANCELLATION = "CANCELLATION"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


class WorkflowStatus(str, Enum):
    """Deterministic status lifecycle of an orchestration workflow execution."""

    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class ExecutionError(BaseModel):
    """Structured record of an unhandled runtime exception, timeout, or cancellation."""

    node: str = Field(..., description="Node ID where execution failure occurred")
    agent: str = Field(..., description="Agent or component type associated with failure")
    error_type: ExecutionErrorType = Field(..., description="Structured error classification")
    message: str = Field(..., description="Original error message without fabrication")
    recoverable: bool = Field(default=False, description="Whether error was recoverable via retry")
    attempt: int = Field(default=1, description="Attempt number when error occurred")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="UTC timestamp of error",
    )
    details: dict[str, Any] = Field(default_factory=dict, description="Optional extra diagnostic details")

    model_config = ConfigDict(extra="ignore")
