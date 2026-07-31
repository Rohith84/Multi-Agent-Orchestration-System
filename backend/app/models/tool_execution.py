"""
ToolExecution SQLAlchemy model.

Stores audit records of every MCP tool invocation,
including the invoking agent, arguments, timing, and result summary.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ToolExecution(Base):
    """
    Represents an MCP tool execution audit record.
    """

    __tablename__ = "tool_executions"

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
    tool_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    arguments: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="{}",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    result_summary: Mapped[str] = mapped_column(
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
        return (
            f"<ToolExecution(id={self.id}, agent={self.agent_name}, "
            f"tool={self.tool_name}, status={self.status})>"
        )
