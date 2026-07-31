"""
ArtifactService — Interactive Artifact Workspace & Multi-Version Manager.

Handles artifact creation, versioning, side-by-side diff generation, restoration, and ZIP/JSON/Markdown exporting.
"""

from __future__ import annotations

import difflib
import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.artifact import Artifact, ArtifactVersion, ArtifactComment
from app.schemas.artifact import ArtifactSchema, ArtifactVersionSchema, ArtifactDiffResponse

logger = get_logger(__name__)


class ArtifactService:
    """
    Manages interactive artifacts, version snapshots, side-by-side diffs, and exports.
    """

    def __init__(self, db: AsyncSession, session_id: uuid.UUID | None = None) -> None:
        self.db = db
        self.session_id = session_id or uuid.uuid4()

    async def create_artifact(
        self,
        title: str,
        content: str,
        artifact_type: str = "code",
        preview_type: str = "html",
        creator_agent: str = "coder",
        change_summary: str = "Initial creation",
    ) -> ArtifactSchema:
        """Create a new artifact with version 1."""
        art = Artifact(
            session_id=self.session_id,
            title=title,
            artifact_type=artifact_type,
            creator_agent=creator_agent,
            current_version=1,
            preview_type=preview_type,
        )
        self.db.add(art)
        await self.db.flush()

        version_1 = ArtifactVersion(
            artifact_id=art.id,
            version=1,
            parent_version=None,
            content=content,
            creator_agent=creator_agent,
            change_summary=change_summary,
        )
        self.db.add(version_1)
        await self.db.commit()

        return await self.get_artifact(art.id)

    async def update_artifact(
        self,
        artifact_id: uuid.UUID,
        new_content: str,
        creator_agent: str = "coder",
        change_summary: str = "Code update",
    ) -> ArtifactSchema:
        """Add a new version to an existing artifact."""
        art = await self._get_artifact_orm(artifact_id)
        if not art:
            raise ValueError(f"Artifact {artifact_id} not found")

        prev_version = art.current_version
        new_version_num = prev_version + 1
        art.current_version = new_version_num
        art.updated_at = datetime.utcnow()

        v = ArtifactVersion(
            artifact_id=art.id,
            version=new_version_num,
            parent_version=prev_version,
            content=new_content,
            creator_agent=creator_agent,
            change_summary=change_summary,
        )
        self.db.add(v)
        await self.db.commit()

        return await self.get_artifact(art.id)

    async def get_artifact(self, artifact_id: uuid.UUID) -> ArtifactSchema:
        """Fetch artifact with all versions."""
        art = await self._get_artifact_orm(artifact_id)
        if not art:
            raise ValueError(f"Artifact {artifact_id} not found")
        return ArtifactSchema.model_validate(art)

    async def list_artifacts() -> list[ArtifactSchema]:
        """List all artifacts for session."""
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.session_id == self.session_id)
            .options(selectinload(Artifact.versions))
            .order_by(Artifact.updated_at.desc())
        )
        artifacts = result.scalars().all()
        return [ArtifactSchema.model_validate(a) for a in artifacts]

    async def get_diff(self, artifact_id: uuid.UUID, version_a: int, version_b: int) -> ArtifactDiffResponse:
        """Compute side-by-side diff between two versions."""
        result = await self.db.execute(
            select(ArtifactVersion).where(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.version.in_([version_a, version_b]),
            )
        )
        versions = {v.version: v.content for v in result.scalars().all()}

        content_a = versions.get(version_a, "")
        content_b = versions.get(version_b, "")

        diff = list(
            difflib.unified_diff(
                content_a.splitlines(),
                content_b.splitlines(),
                fromfile=f"Version {version_a}",
                tofile=f"Version {version_b}",
                lineterm="",
            )
        )

        return ArtifactDiffResponse(
            artifact_id=str(artifact_id),
            version_a=version_a,
            version_b=version_b,
            content_a=content_a,
            content_b=content_b,
            diff_lines=diff,
        )

    async def restore_version(self, artifact_id: uuid.UUID, target_version: int) -> ArtifactSchema:
        """Restore artifact content to a previous version."""
        result = await self.db.execute(
            select(ArtifactVersion).where(
                ArtifactVersion.artifact_id == artifact_id,
                ArtifactVersion.version == target_version,
            )
        )
        target = result.scalar_one_or_none()
        if not target:
            raise ValueError(f"Version {target_version} not found")

        return await self.update_artifact(
            artifact_id=artifact_id,
            new_content=target.content,
            change_summary=f"Restored from version {target_version}",
        )

    async def _get_artifact_orm(self, artifact_id: uuid.UUID) -> Artifact | None:
        result = await self.db.execute(
            select(Artifact)
            .where(Artifact.id == artifact_id)
            .options(selectinload(Artifact.versions))
        )
        return result.scalar_one_or_none()
