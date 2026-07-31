"""
WorkspaceFile, WorkspaceSnapshot, TestReport, and QualityReport SQLAlchemy models.

Manages tracked project files, workspace state snapshots, test suite execution reports, and static analysis quality gate findings.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Uuid, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class WorkspaceFile(Base):
    """
    Tracks a generated or modified file inside the workspace.
    """

    __tablename__ = "workspace_files"

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
    file_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="python",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
    )  # active, deleted, modified
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
        return f"<WorkspaceFile(path={self.file_path}, version={self.version}, lang={self.language})>"


class WorkspaceSnapshot(Base):
    """
    Workspace snapshot for instantaneous state rollback.
    """

    __tablename__ = "workspace_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    snapshot_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    file_manifest: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )  # path -> content
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<WorkspaceSnapshot(id={self.id}, name={self.snapshot_name})>"


class TestReport(Base):
    """
    Execution outputs and structured bug reports from Testing Agent.
    """

    __tablename__ = "test_reports"

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
    project_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="python",
    )
    test_command: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="pytest",
    )
    passed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    execution_time: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    stdout: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    stderr: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    bug_report: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )  # failed_file, stack_trace, suggested_fix, etc.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<TestReport(workflow_id={self.workflow_id}, passed={self.passed}, cmd={self.test_command})>"


class QualityReport(Base):
    """
    Static analysis findings (Ruff, Bandit) and Quality Gate status from Reviewer Agent.
    """

    __tablename__ = "quality_reports"

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
    quality_gate: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="PASS",
    )  # PASS, PASS_WITH_WARNINGS, FAIL
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=9.0,
    )
    lint_findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Ruff / Pylint output
    security_findings: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )  # Bandit output
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<QualityReport(workflow_id={self.workflow_id}, gate={self.quality_gate}, score={self.overall_score})>"
