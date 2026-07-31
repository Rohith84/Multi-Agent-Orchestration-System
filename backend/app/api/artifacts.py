"""
Artifact Workspace, Vision Analysis, and Version Control API Endpoints.

Provides:
- GET /api/artifacts                  — list session artifacts
- POST /api/artifacts                 — create new interactive artifact
- GET /api/artifacts/{id}             — fetch artifact details & content
- POST /api/artifacts/{id}/restore     — restore previous version
- GET /api/artifacts/{id}/diff        — compute side-by-side version diff
- POST /api/artifacts/vision/analyze  — vision image/diagram analysis
"""

from __future__ import annotations

import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.artifact import (
    ArtifactSchema,
    CreateArtifactRequest,
    RestoreVersionRequest,
    ArtifactDiffResponse,
    VisionAnalyzeRequest,
)
from app.services.artifact_service import ArtifactService
from app.services.vision_service import VisionAnalysisService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("", response_model=list[ArtifactSchema])
async def list_artifacts(
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> list[ArtifactSchema]:
    """List all interactive artifacts for the current session."""
    sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
    service = ArtifactService(db, session_id=sid)
    return await service.list_artifacts()


@router.post("", response_model=ArtifactSchema)
async def create_artifact(
    request: CreateArtifactRequest,
    session_id: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> ArtifactSchema:
    """Create a new artifact."""
    sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
    service = ArtifactService(db, session_id=sid)
    return await service.create_artifact(
        title=request.title,
        content=request.content,
        artifact_type=request.artifact_type,
        preview_type=request.preview_type,
        creator_agent=request.creator_agent,
        change_summary=request.change_summary,
    )


@router.get("/{artifact_id}", response_model=ArtifactSchema)
async def get_artifact_details(
    artifact_id: str,
    db: AsyncSession = Depends(get_db),
) -> ArtifactSchema:
    """Fetch artifact details with complete version history."""
    try:
        aid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    service = ArtifactService(db)
    try:
        return await service.get_artifact(aid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{artifact_id}/restore", response_model=ArtifactSchema)
async def restore_artifact_version(
    artifact_id: str,
    request: RestoreVersionRequest,
    db: AsyncSession = Depends(get_db),
) -> ArtifactSchema:
    """Restore an artifact to a previous version."""
    try:
        aid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    service = ArtifactService(db)
    try:
        return await service.restore_version(aid, request.version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{artifact_id}/diff", response_model=ArtifactDiffResponse)
async def get_artifact_diff(
    artifact_id: str,
    version_a: int = Query(default=1, ge=1),
    version_b: int = Query(default=2, ge=1),
    db: AsyncSession = Depends(get_db),
) -> ArtifactDiffResponse:
    """Get side-by-side diff between two artifact versions."""
    try:
        aid = uuid.UUID(artifact_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid artifact ID format")

    service = ArtifactService(db)
    return await service.get_diff(aid, version_a, version_b)


@router.post("/vision/analyze")
async def analyze_vision_image(
    request: VisionAnalyzeRequest,
) -> dict[str, Any]:
    """Analyze base64 uploaded image/sketch/diagram using vision service."""
    service = VisionAnalysisService()
    return await service.analyze_image(
        image_base64=request.image_base64,
        file_type=request.file_type,
        prompt=request.prompt,
    )
