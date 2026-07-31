"""
Tool Service — business logic for MCP tool operations.

Orchestrates between the MCP server, tool repository, and API layer.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.mcp.server import get_mcp_server, MCPRequest
from app.repositories.tool_repository import ToolExecutionRepository
from app.schemas.tools import (
    ToolSchema,
    ToolListResponse,
    ToolRunResponse,
    ToolExecutionSchema,
    ToolHistoryResponse,
)

logger = get_logger(__name__)


class ToolService:
    """
    Service layer for MCP tool operations.

    Coordinates between:
    - MCPServer: executing tools
    - ToolExecutionRepository: persisting execution logs
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ToolExecutionRepository(db)
        self.server = get_mcp_server()

    def list_tools(self) -> ToolListResponse:
        """Return all registered MCP tools."""
        tool_dicts = self.server.list_tools()
        tools = [ToolSchema(**t) for t in tool_dicts]
        return ToolListResponse(tools=tools, count=len(tools))

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        agent_name: str = "manual",
    ) -> ToolRunResponse:
        """
        Execute an MCP tool and log the result.

        Args:
            tool_name: Name of the tool.
            arguments: Tool arguments.
            agent_name: Agent name for audit (default 'manual').

        Returns:
            ToolRunResponse with result or error.
        """
        request = MCPRequest(
            method=tool_name,
            params=arguments,
            id=f"{agent_name}-{tool_name}",
        )

        response = await self.server.handle_request(request)

        # Build result summary
        if response.success:
            summary = self._summarize(response.result)
        else:
            summary = response.error or "Unknown error"

        # Persist execution record
        await self.repository.save_execution(
            agent_name=agent_name,
            tool_name=tool_name,
            arguments=arguments,
            status="success" if response.success else "failed",
            execution_time=response.execution_time,
            result_summary=summary[:1000],
        )
        await self.db.commit()

        return ToolRunResponse(
            success=response.success,
            tool_name=tool_name,
            result=response.result if response.success else None,
            error=response.error if not response.success else None,
            execution_time=round(response.execution_time, 4),
        )

    async def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> ToolHistoryResponse:
        """Return paginated tool execution history."""
        records, total = await self.repository.get_history(
            limit=limit,
            offset=offset,
            search=search,
        )

        executions = [
            ToolExecutionSchema(
                id=str(r.id),
                agent_name=r.agent_name,
                tool_name=r.tool_name,
                arguments=r.arguments,
                status=r.status,
                execution_time=r.execution_time,
                result_summary=r.result_summary,
                created_at=r.created_at,
            )
            for r in records
        ]

        return ToolHistoryResponse(
            executions=executions,
            total=total,
            limit=limit,
            offset=offset,
        )

    def _summarize(self, result: Any, max_len: int = 1000) -> str:
        """Create a brief summary of a tool result."""
        if result is None:
            return "No result"
        if isinstance(result, str):
            return result[:max_len]
        if isinstance(result, dict):
            summary = {}
            for key, value in result.items():
                if isinstance(value, str) and len(value) > 200:
                    summary[key] = f"[{len(value)} chars]"
                elif isinstance(value, list) and len(value) > 10:
                    summary[key] = f"[{len(value)} items]"
                else:
                    summary[key] = value
            return json.dumps(summary, default=str)[:max_len]
        return str(result)[:max_len]
