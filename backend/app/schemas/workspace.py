"""
Pydantic schemas for Workspace, Test Execution, Static Analysis, and Quality Gate contracts.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceFileSchema(BaseModel):
    """Schema for a tracked file in the project workspace."""

    id: uuid.UUID | str
    session_id: uuid.UUID | str
    file_path: str
    content: str
    language: str
    version: int
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkspaceSnapshotSchema(BaseModel):
    """Schema for a workspace state snapshot."""

    id: uuid.UUID | str
    snapshot_name: str
    file_manifest: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BugReportSchema(BaseModel):
    """Structured bug report schema generated when unit tests fail."""

    failed_file: str = Field(default="", description="Path to the file that caused test failure.")
    failed_test: str = Field(default="", description="Name of the failing test function.")
    stack_trace: str = Field(default="", description="Captured stderr/stack trace output.")
    error_category: str = Field(default="AssertionError", description="High-level failure categorization.")
    suggested_fix: str = Field(default="", description="Recommended code fix or patch.")
    severity: str = Field(default="HIGH", description="Bug severity: LOW, MEDIUM, HIGH, CRITICAL.")


class TestReportSchema(BaseModel):
    """Schema for test execution output."""

    id: uuid.UUID | str
    workflow_id: uuid.UUID | str
    project_type: str
    test_command: str
    passed: bool
    execution_time: float
    stdout: str
    stderr: str
    bug_report: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QualityReportSchema(BaseModel):
    """Schema for static analysis findings and quality gate decisions."""

    id: uuid.UUID | str
    workflow_id: uuid.UUID | str
    quality_gate: str
    overall_score: float
    lint_findings: list[dict[str, Any]]
    security_findings: list[dict[str, Any]]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RollbackRequest(BaseModel):
    """Request to rollback workspace to a snapshot."""

    snapshot_id: str = Field(..., description="ID of the snapshot to restore.")
