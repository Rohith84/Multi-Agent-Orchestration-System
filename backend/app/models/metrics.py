"""
AgentMetric, WorkflowMetric, and PromptVersion SQLAlchemy models.

Stores evaluation scores, token counts, latencies, tool execution metrics, RAG metrics, and versioned prompt templates.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Uuid, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AgentMetric(Base):
    """
    Performance and quality metrics for a single agent execution step.
    """

    __tablename__ = "agent_metrics"

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
        index=True,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    duration: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # success, failed, retried
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    tool_calls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    knowledge_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=8.5,
    )  # LLM-as-a-Judge quality score (1.0 to 10.0)
    eval_breakdown: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )  # accuracy, reasoning, structure, usefulness
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AgentMetric(id={self.id}, agent={self.agent_name}, model={self.model}, duration={self.duration}s, score={self.score})>"


class WorkflowMetric(Base):
    """
    Aggregated performance and evaluation metrics for a complete workflow.
    """

    __tablename__ = "workflow_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        unique=True,
        index=True,
    )
    total_duration: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    approval_wait_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    tool_execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    rag_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=9.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowMetric(workflow_id={self.workflow_id}, duration={self.total_duration}s, tokens={self.total_tokens}, score={self.overall_score})>"


class PromptVersion(Base):
    """
    Prompt Registry version model for agent system prompts.
    """

    __tablename__ = "prompt_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )
    version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )  # e.g. "v1.0", "v2.0"
    template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PromptVersion(agent={self.agent_name}, version={self.version}, active={self.active})>"
