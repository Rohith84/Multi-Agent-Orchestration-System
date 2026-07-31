"""
MCP Tools API endpoints.

Provides:
- GET /api/tools          — list all available MCP tools
- POST /api/tools/run     — execute a tool manually
- GET /api/tools/history  — view tool execution history
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.tools import (
    ToolListResponse,
    ToolRunRequest,
    ToolRunResponse,
    ToolHistoryResponse,
)
from app.mcp.services.tool_service import ToolService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/tools", tags=["tools"])


def _get_tool_service(db: AsyncSession = Depends(get_db)) -> ToolService:
    return ToolService(db)


@router.get("", response_model=ToolListResponse)
async def list_tools(
    service: ToolService = Depends(_get_tool_service),
) -> ToolListResponse:
    """
    List all available MCP tools with their parameter schemas.
    """
    return service.list_tools()


@router.post("/run", response_model=ToolRunResponse)
async def run_tool(
    request: ToolRunRequest,
    service: ToolService = Depends(_get_tool_service),
) -> ToolRunResponse:
    """
    Execute an MCP tool with the provided arguments.
    Results are logged to the tool_executions table.
    """
    logger.info(
        "Manual tool execution: tool=%s agent=%s",
        request.tool_name,
        request.agent_name,
    )
    return await service.execute_tool(
        tool_name=request.tool_name,
        arguments=request.arguments,
        agent_name=request.agent_name,
    )


@router.get("/history", response_model=ToolHistoryResponse)
async def get_tool_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None),
    service: ToolService = Depends(_get_tool_service),
) -> ToolHistoryResponse:
    """
    Get paginated tool execution history with optional search.
    """
    return await service.get_history(limit=limit, offset=offset, search=search)
