"""
Analytics and Observability API Endpoints.

Provides:
- GET /api/analytics/dashboard — system metrics, LLMOps comparison, tool & RAG stats
- GET /api/analytics/export — export metrics report as JSON or CSV
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.analytics import DashboardAnalyticsResponse
from app.services.analytics_service import AnalyticsService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _get_analytics_service(db: AsyncSession = Depends(get_db)) -> AnalyticsService:
    return AnalyticsService(db)


@router.get("/dashboard", response_model=DashboardAnalyticsResponse)
async def get_dashboard_analytics(
    service: AnalyticsService = Depends(_get_analytics_service),
) -> DashboardAnalyticsResponse:
    """
    Get aggregated system analytics, token usage, LLM model performance comparison, tool metrics, and evaluation quality scores.
    """
    return await service.get_dashboard_analytics()


@router.get("/export")
async def export_analytics_report(
    format: str = Query(default="json", description="Export format: 'json' or 'csv'"),
    service: AnalyticsService = Depends(_get_analytics_service),
) -> PlainTextResponse:
    """
    Export metrics observability report as JSON or CSV string.
    """
    content = await service.export_report(format_type=format)
    media_type = "text/csv" if format.lower() == "csv" else "application/json"
    filename = f"analytics_report_{format.lower()}.{format.lower()}"

    return PlainTextResponse(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
