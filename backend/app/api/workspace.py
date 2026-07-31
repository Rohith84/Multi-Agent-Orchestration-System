"""
Workspace, Test Reports, Quality Gate, and Snapshot Rollback API Endpoints.

Provides:
- GET /api/workspace          — list active workspace files
- GET /api/workspace/files    — read file content
- POST /api/workspace/rollback — restore files from snapshot
- GET /api/tests              — test execution reports
- GET /api/reviews            — quality gate reports & linters output
- GET /api/quality            — quality gate summary metrics
"""

from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.models.workspace import WorkspaceFile, WorkspaceSnapshot, TestReport, QualityReport
from app.schemas.workspace import (
    WorkspaceFileSchema,
    WorkspaceSnapshotSchema,
    TestReportSchema,
    QualityReportSchema,
    RollbackRequest,
)
from app.services.workspace_service import WorkspaceService

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["workspace"])


@router.get("/workspace", response_model=list[WorkspaceFileSchema])
async def list_workspace_files(
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceFileSchema]:
    """List active files in the workspace."""
    sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
    service = WorkspaceService(db, session_id=sid)
    return await service.list_files()


@router.get("/workspace/files")
async def get_workspace_file_content(
    path: str,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Read specific file content from workspace sandbox."""
    sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
    service = WorkspaceService(db, session_id=sid)
    try:
        target = service._resolve_safe_path(path)
        if not target.exists():
            raise HTTPException(status_code=404, detail="File not found")
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workspace/rollback")
async def rollback_workspace(
    request: RollbackRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Rollback workspace files to a snapshot state."""
    try:
        snap_id = uuid.UUID(request.snapshot_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid snapshot ID format")

    service = WorkspaceService(db)
    success = await service.rollback(snap_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return {"status": "success", "message": "Workspace restored from snapshot"}


@router.get("/tests", response_model=list[TestReportSchema])
async def list_test_reports(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[TestReportSchema]:
    """Get history of test execution reports."""
    result = await db.execute(
        select(TestReport).order_by(TestReport.created_at.desc()).limit(limit)
    )
    reports = result.scalars().all()
    return [TestReportSchema.model_validate(r) for r in reports]


@router.get("/reviews", response_model=list[QualityReportSchema])
async def list_quality_reports(
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[QualityReportSchema]:
    """Get history of quality reports and static linter findings."""
    result = await db.execute(
        select(QualityReport).order_by(QualityReport.created_at.desc()).limit(limit)
    )
    reports = result.scalars().all()
    return [QualityReportSchema.model_validate(r) for r in reports]


@router.get("/quality")
async def get_quality_gate_summary(
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get overall quality gate metrics and linter summary stats."""
    result = await db.execute(select(QualityReport).order_by(QualityReport.created_at.desc()).limit(50))
    reports = result.scalars().all()

    pass_count = sum(1 for r in reports if r.quality_gate == "PASS")
    warn_count = sum(1 for r in reports if r.quality_gate == "PASS_WITH_WARNINGS")
    fail_count = sum(1 for r in reports if r.quality_gate == "FAIL")

    return {
        "total_reviews": len(reports),
        "pass_count": pass_count,
        "pass_with_warnings_count": warn_count,
        "fail_count": fail_count,
        "pass_rate_percentage": round((pass_count / max(1, len(reports))) * 100, 1),
    }
