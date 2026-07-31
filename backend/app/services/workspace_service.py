"""
WorkspaceService — Isolated Sandbox Project Workspace Manager.

Manages file creation, modifications, directory structures, version tracking, snapshot creation, and instantaneous rollback capabilities.
"""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.workspace import WorkspaceFile, WorkspaceSnapshot
from app.schemas.workspace import WorkspaceFileSchema, WorkspaceSnapshotSchema

logger = get_logger(__name__)

SANDBOX_DIR = Path("sandbox_workspace").resolve()


class WorkspaceService:
    """
    Manages isolated project workspace files in sandbox_workspace/ and DB state.
    """

    def __init__(self, db: AsyncSession, session_id: uuid.UUID | None = None) -> None:
        self.db = db
        self.session_id = session_id or uuid.uuid4()
        self.workspace_dir = SANDBOX_DIR
        self.workspace_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve path and ensure it stays inside sandbox workspace."""
        clean_rel = relative_path.lstrip("/\\")
        target_path = (self.workspace_dir / clean_rel).resolve()
        if not str(target_path).startswith(str(self.workspace_dir)):
            raise ValueError(f"Path traversal denied outside workspace: {relative_path}")
        return target_path

    async def write_file(self, relative_path: str, content: str, language: str = "python") -> WorkspaceFileSchema:
        """Write file to disk and record version in DB."""
        target_path = self._resolve_safe_path(relative_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        target_path.write_text(content, encoding="utf-8")
        logger.info("Workspace file written: %s (%d bytes)", relative_path, len(content))

        # Check existing version
        result = await self.db.execute(
            select(WorkspaceFile).where(
                WorkspaceFile.session_id == self.session_id,
                WorkspaceFile.file_path == relative_path,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.content = content
            existing.version += 1
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            return WorkspaceFileSchema.model_validate(existing)
        else:
            wf = WorkspaceFile(
                session_id=self.session_id,
                file_path=relative_path,
                content=content,
                language=language,
                version=1,
                status="active",
            )
            self.db.add(wf)
            await self.db.commit()
            return WorkspaceFileSchema.model_validate(wf)

    async def list_files(self) -> list[WorkspaceFileSchema]:
        """List all active files in the workspace."""
        result = await self.db.execute(
            select(WorkspaceFile)
            .where(WorkspaceFile.session_id == self.session_id, WorkspaceFile.status == "active")
            .order_by(WorkspaceFile.file_path.asc())
        )
        files = result.scalars().all()
        return [WorkspaceFileSchema.model_validate(f) for f in files]

    async def create_snapshot(self, snapshot_name: str) -> WorkspaceSnapshotSchema:
        """Create a state snapshot of all workspace files."""
        files = await self.list_files()
        manifest = {f.file_path: f.content for f in files}

        snapshot = WorkspaceSnapshot(
            snapshot_name=snapshot_name,
            file_manifest=manifest,
        )
        self.db.add(snapshot)
        await self.db.commit()
        logger.info("Created workspace snapshot '%s' ID=%s", snapshot_name, snapshot.id)
        return WorkspaceSnapshotSchema.model_validate(snapshot)

    async def rollback(self, snapshot_id: uuid.UUID) -> bool:
        """Restore all files to state recorded in snapshot."""
        result = await self.db.execute(
            select(WorkspaceSnapshot).where(WorkspaceSnapshot.id == snapshot_id)
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            return False

        manifest = snapshot.file_manifest
        for rel_path, content in manifest.items():
            await self.write_file(rel_path, content)

        logger.info("Rolled back workspace to snapshot ID=%s", snapshot_id)
        return True
