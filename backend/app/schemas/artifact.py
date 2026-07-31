"""
Pydantic schemas for Artifacts, Versions, Side-by-Side Diffs, and Vision Requests.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactVersionSchema(BaseModel):
    """Schema for an artifact version snapshot."""

    id: str
    artifact_id: str
    version: int
    parent_version: int | None = None
    content: str
    creator_agent: str
    change_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ArtifactSchema(BaseModel):
    """Schema for a managed interactive artifact."""

    id: str
    session_id: str
    title: str
    artifact_type: str
    creator_agent: str
    current_version: int
    preview_type: str
    created_at: datetime
    updated_at: datetime
    versions: list[ArtifactVersionSchema] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class CreateArtifactRequest(BaseModel):
    """Request payload to create a new artifact."""

    title: str = Field(..., description="Title of the artifact.")
    artifact_type: str = Field(default="code", description="Artifact type: code, diagram, markdown, pdf, json, image.")
    preview_type: str = Field(default="html", description="Preview type: html, mermaid, text, markdown.")
    content: str = Field(..., description="Initial version content.")
    creator_agent: str = Field(default="coder", description="Agent that created the artifact.")
    change_summary: str = Field(default="Initial creation", description="Summary of changes.")


class RestoreVersionRequest(BaseModel):
    """Request to restore a specific version."""

    version: int = Field(..., description="Target version number to restore.")


class ArtifactDiffResponse(BaseModel):
    """Side-by-side diff comparison between two versions."""

    artifact_id: str
    version_a: int
    version_b: int
    content_a: str
    content_b: str
    diff_lines: list[str] = Field(default_factory=list)


class VisionAnalyzeRequest(BaseModel):
    """Request payload for vision image/diagram analysis."""

    image_base64: str = Field(..., description="Base64 encoded image or diagram data.")
    file_type: str = Field(default="png", description="Image extension: png, jpeg, svg, pdf.")
    prompt: str = Field(default="Analyze this UI layout or architecture diagram.", description="Instructions for vision model.")
