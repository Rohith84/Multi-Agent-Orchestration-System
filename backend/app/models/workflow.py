"""
Workflow, WorkflowCheckpoint, WorkflowApproval, PlanningMemory, and WorkflowSchedule SQLAlchemy models.

Stores workflow states, state checkpoints, approval gate requests,
planning memory for RAG reuse, and automated workflow schedule configurations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, Uuid, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Workflow(Base):
    """
    Represents an execution workflow instance.
    """

    __tablename__ = "workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Multi-Agent Workflow",
    )
    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        index=True,
    )  # pending, running, paused_approval, completed, failed, cancelled
    current_agent: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="planner",
    )
    progress_percentage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    require_approval_agents: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # e.g. ["coder", "tester"]
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Workflow(id={self.id}, title={self.title}, status={self.status}, progress={self.progress_percentage}%)>"


class WorkflowCheckpoint(Base):
    """
    State checkpoint persisted after every agent execution.
    """

    __tablename__ = "workflow_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    shared_state: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    tool_history: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    research_context: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    chat_context: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowCheckpoint(id={self.id}, workflow_id={self.workflow_id}, agent={self.agent_name})>"


class WorkflowApproval(Base):
    """
    Approval gate record for Human-in-the-Loop workflows.
    """

    __tablename__ = "workflow_approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
    )  # pending, approved, rejected
    comments: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<WorkflowApproval(id={self.id}, workflow_id={self.workflow_id}, agent={self.agent_name}, status={self.status})>"


class PlanningMemory(Base):
    """
    Historical plan store used for similarity search and architectural pattern reuse.
    """

    __tablename__ = "planning_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    goal: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    plan: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    success_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PlanningMemory(id={self.id}, goal={self.goal[:30]}...)>"


class WorkflowSchedule(Base):
    """
    Scheduled or recurring workflow rule.
    """

    __tablename__ = "workflow_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    user_request: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    cron_expression: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="0 0 * * *",
    )  # e.g. "0 0 * * *" or "interval:60"
    require_approval_agents: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )  # active, paused, completed
    last_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowSchedule(id={self.id}, title={self.title}, status={self.status})>"
