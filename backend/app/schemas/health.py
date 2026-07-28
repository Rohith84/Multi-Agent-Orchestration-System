"""
Pydantic schemas for health and system status endpoints.

These schemas define the API response contracts.
"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for GET /api/health."""

    status: str = Field(default="ok", examples=["ok"])
    message: str = Field(default="Backend is running", examples=["Backend is running"])


class SubsystemStatus(BaseModel):
    """Status of a single subsystem (DB, Ollama, etc.)."""

    name: str = Field(..., examples=["database"])
    status: str = Field(..., examples=["connected"])
    message: str = Field(..., examples=["PostgreSQL is connected"])


class SystemStatusResponse(BaseModel):
    """
    Aggregated system status response for GET /api/system-status.

    Contains status of all subsystems: backend, database, ollama.
    """

    backend: SubsystemStatus
    database: SubsystemStatus
    ollama: SubsystemStatus
    system_ready: bool = Field(
        ...,
        description="True when all critical subsystems are operational",
    )
