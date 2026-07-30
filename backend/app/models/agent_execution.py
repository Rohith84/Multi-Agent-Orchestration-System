"""
AgentExecution SQLAlchemy model.

Stores details of every individual agent's execution within a workflow,
including input context, generated outputs, duration, and status.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class AgentExecution(Base):
    """
    Represents the execution record of an AI agent in a workflow step.
    """

    __tablename__ = "agent_executions"

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
    agent_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    input_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    output_content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AgentExecution(id={self.id}, session_id={self.session_id}, agent={self.agent_name}, status={self.status})>"
