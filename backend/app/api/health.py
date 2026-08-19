"""
Health, Liveness, and Readiness API Probes.

Provides:
- GET /api/health         — comprehensive system health details
- GET /api/liveness       — lightweight liveness probe (200 OK)
- GET /api/readiness      — readiness probe checking PostgreSQL & Redis (200 OK or 503 Service Unavailable)
- GET /api/system-status — aggregated status of all subsystems
"""

from typing import Any
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.schemas.health import (
    HealthResponse,
    SubsystemStatus,
    SystemStatusResponse,
)
from app.core.cache import get_redis_connection

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Simple health probe."""
    return HealthResponse(status="ok", message="Backend is healthy")


@router.get("/liveness")
async def liveness_probe() -> dict[str, str]:
    """Lightweight liveness probe."""
    return {"status": "alive"}


@router.get("/readiness")
async def readiness_probe(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Readiness probe testing database and cache readiness.
    Returns HTTP 200 if ready, or 503 if critical dependencies are down.
    """
    db_ok = False
    redis_ok = False

    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    try:
        redis_conn = await get_redis_connection()
        if redis_conn:
            redis_ok = True
    except Exception:
        redis_ok = False

    ready = db_ok

    if not ready:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "database": db_ok, "redis": redis_ok},
        )

    return {"status": "ready", "database": db_ok, "redis": redis_ok}


@router.get("/system-status", response_model=SystemStatusResponse)
async def system_status(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    """Aggregated system status check."""
    backend_status = SubsystemStatus(
        name="backend",
        status="connected",
        message="FastAPI is running",
    )
    try:
        database_status = await _check_database(db)
    except Exception as e:
        database_status = SubsystemStatus(name="database", status="disconnected", message=str(e)[:100])

    try:
        ollama_status = await _check_ollama(settings.ollama_base_url)
    except Exception as e:
        ollama_status = SubsystemStatus(name="ollama", status="disconnected", message=str(e)[:100])

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


@router.get("/ollama/runtime")
async def get_ollama_runtime_diagnostics() -> dict[str, Any]:
    """Returns real-time Ollama GPU/CPU runtime process status."""
    from app.ai.ollama_client import OllamaClient
    client = OllamaClient()
    return await client.get_runtime_status()
