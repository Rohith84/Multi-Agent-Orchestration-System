"""
Health and system status API endpoints.

Provides:
- GET /api/health      — simple liveness check
- GET /api/system-status — aggregated status of all subsystems
"""

import httpx
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.health import (
    HealthResponse,
    SubsystemStatus,
    SystemStatusResponse,
)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Simple liveness probe.

    Returns 200 with status "ok" if the backend process is running.
    Does NOT check database or external services.
    """
    return HealthResponse(status="ok", message="Backend is running")


@router.get("/system-status", response_model=SystemStatusResponse)
async def system_status(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    """
    Aggregated system status check.

    Checks:
    - Backend: always ok (if this endpoint responds)
    - Database: attempts a simple query
    - Ollama: attempts to reach the Ollama API

    Returns a combined status with a system_ready flag.
    """
    # Backend is always ok if we get here
    backend_status = SubsystemStatus(
        name="backend",
        status="connected",
        message="FastAPI is running",
    )

    # Check database
    database_status = await _check_database(db)

    # Check Ollama
    ollama_status = await _check_ollama(settings.ollama_base_url)

    # System is ready when all critical services are up (Ollama is optional)
    system_ready = (
        backend_status.status == "connected"
        and database_status.status == "connected"
    )

    return SystemStatusResponse(
        backend=backend_status,
        database=database_status,
        ollama=ollama_status,
        system_ready=system_ready,
    )


async def _check_database(db: AsyncSession) -> SubsystemStatus:
    """Test database connectivity with a simple query."""
    try:
        await db.execute(text("SELECT 1"))
        return SubsystemStatus(
            name="database",
            status="connected",
            message="PostgreSQL is connected",
        )
    except Exception as e:
        return SubsystemStatus(
            name="database",
            status="disconnected",
            message=f"PostgreSQL connection failed: {str(e)[:100]}",
        )


async def _check_ollama(base_url: str) -> SubsystemStatus:
    """Test Ollama API reachability."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                return SubsystemStatus(
                    name="ollama",
                    status="connected",
                    message="Ollama is running",
                )
            return SubsystemStatus(
                name="ollama",
                status="disconnected",
                message=f"Ollama returned status {response.status_code}",
            )
    except Exception:
        return SubsystemStatus(
            name="ollama",
            status="disconnected",
            message="Ollama is not reachable",
        )
