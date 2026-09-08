"""
Pydantic schemas for Production Observability and Execution Audit Trail.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExecutionEventType(str, Enum):
    """Event classifications for workflow audit trace logging."""

    WORKFLOW_STARTED = "WORKFLOW_STARTED"
    NODE_STARTED = "NODE_STARTED"
    NODE_COMPLETED = "NODE_COMPLETED"
    NODE_FAILED = "NODE_FAILED"
    NODE_RETRIED = "NODE_RETRIED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_COMPLETED = "TOOL_COMPLETED"
    TOOL_FAILED = "TOOL_FAILED"
    CONTRACT_VALIDATED = "CONTRACT_VALIDATED"
    CONTRACT_FAILED = "CONTRACT_FAILED"
    RAG_COMPLETED = "RAG_COMPLETED"
    QUALITY_GATE_COMPLETED = "QUALITY_GATE_COMPLETED"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    WORKFLOW_COMPLETED = "WORKFLOW_COMPLETED"
    WORKFLOW_FAILED = "WORKFLOW_FAILED"
    WORKFLOW_BLOCKED = "WORKFLOW_BLOCKED"
    WORKFLOW_CANCELLED = "WORKFLOW_CANCELLED"


class ExecutionEvent(BaseModel):
    """Structured, serializable record of a workflow execution step or event."""

    event_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for trace event",
    )
    session_id: str = Field(..., description="Session identifier")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="UTC timestamp of event",
    )
    event_type: ExecutionEventType = Field(..., description="Event category classification")
    node_id: str | None = Field(default=None, description="Graph node ID if applicable")
    agent_type: str | None = Field(default=None, description="Agent or tool component type")
    status: str = Field(default="SUCCESS", description="Event status outcome")
    duration_ms: float | None = Field(default=None, description="Duration in milliseconds")
    attempt: int | None = Field(default=None, description="Attempt number for retries")
    message: str | None = Field(default=None, description="Human-readable event message")
    evidence: dict[str, Any] | None = Field(default=None, description="Structured non-sensitive evidence metadata")

    model_config = ConfigDict(extra="ignore", use_enum_values=True)


class ExecutionSummary(BaseModel):
    """Deterministic summary derived strictly from recorded execution trace evidence."""

    session_id: str = Field(..., description="Session identifier")
    workflow_status: str = Field(..., description="Final workflow lifecycle status")
    duration_ms: float = Field(default=0.0, description="Total workflow duration in ms")
    nodes_executed: int = Field(default=0, description="Count of distinct nodes executed")
    nodes_failed: int = Field(default=0, description="Count of failed node attempts")
    retries: int = Field(default=0, description="Total retry attempts executed")
    contract_results: dict[str, str] = Field(
        default_factory=dict,
        description="Deterministic contract statuses (plan, graph, code)",
    )
    rag_status: str | None = Field(default=None, description="Authoritative RAG retrieval status")
    quality_gate: str | None = Field(default=None, description="Authoritative Quality Gate result")
    reviewer_decision: str | None = Field(default=None, description="Non-authoritative Reviewer status")
    errors: list[dict[str, Any]] = Field(default_factory=list, description="Recorded execution errors")

    model_config = ConfigDict(extra="ignore")
