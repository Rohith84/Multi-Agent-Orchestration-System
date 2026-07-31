"""
Artifact, ArtifactVersion, and ArtifactComment SQLAlchemy models.

Manages interactive artifacts (UI code, Mermaid diagrams, architecture specs, PDF reports) with full multi-versioning history and collaboration notes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, Uuid, func, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Artifact(Base):
    """
    Primary artifact entity tracking current version state.
    """

    __tablename__ = "artifacts"

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
    )
    artifact_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="code",
    )  # code, diagram, markdown, pdf, json, image
    creator_agent: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="coder",
    )
    current_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    preview_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="html",
    )  # html, mermaid, text, markdown
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

    versions = relationship("ArtifactVersion", back_populates="artifact", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Artifact(id={self.id}, title='{self.title}', type='{self.artifact_type}', v={self.current_version})>"


class ArtifactVersion(Base):
    """
    Version snapshot of an artifact's content.
    """

    __tablename__ = "artifact_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    parent_version: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    creator_agent: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="coder",
    )
    change_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Initial creation",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    artifact = relationship("Artifact", back_populates="versions")

    def __repr__(self) -> str:
        return f"<ArtifactVersion(artifact_id={self.artifact_id}, version={self.version})>"


class ArtifactComment(Base):
    """
    User/Agent feedback comment attached to an artifact version.
    """

    __tablename__ = "artifact_comments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("artifacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    author: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="user",
    )
    comment: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ArtifactComment(artifact_id={self.artifact_id}, author='{self.author}')>"
