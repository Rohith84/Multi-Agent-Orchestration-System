"""
WorkflowTemplate, CustomAgent, and WorkflowRun SQLAlchemy models.

Manages dynamic workflow graph templates, custom agent prompt/tool definitions, and execution run histories.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Uuid, func, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WorkflowTemplate(Base):
    """
    Saved visual workflow graph template definition.
    """

    __tablename__ = "workflow_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    graph_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )  # nodes, edges, config
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    is_preset: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
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
        return f"<WorkflowTemplate(id={self.id}, name='{self.name}', v={self.version})>"


class CustomAgent(Base):
    """
    User-defined agent with custom system prompt, LLM model, and MCP tool permissions.
    """

    __tablename__ = "custom_agents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    system_prompt: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    user_prompt_template: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{input}",
    )
    llm_model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="llama3.1:8b",
    )
    temperature: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.7,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
    )
    allowed_mcp_tools: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<CustomAgent(id={self.id}, name='{self.name}', model='{self.llm_model}')>"


class WorkflowRun(Base):
    """
    Execution run instance of a dynamic workflow template.
    """

    __tablename__ = "workflow_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workflow_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="completed",
    )  # running, completed, failed
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    nodes_executed: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkflowRun(id={self.id}, template_id={self.template_id}, status='{self.status}')>"
