"""
ToolExecution repository — data access layer for MCP tool invocation audit records.
"""

import json
import uuid
from typing import Any

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.tool_execution import ToolExecution

logger = get_logger(__name__)


class ToolExecutionRepository:
    """
    Handles persistence and query operations for ToolExecution records.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_execution(
        self,
        agent_name: str,
        tool_name: str,
        arguments: dict[str, Any],
        status: str,
        execution_time: float,
        result_summary: str,
    ) -> ToolExecution:
        """Save a tool execution record."""
        record = ToolExecution(
            agent_name=agent_name,
            tool_name=tool_name,
            arguments=json.dumps(arguments, default=str),
            status=status,
            execution_time=execution_time,
            result_summary=result_summary,
        )
        self.db.add(record)
        await self.db.flush()
        logger.debug(
            "Saved tool execution: agent=%s tool=%s status=%s",
            agent_name,
            tool_name,
            status,
        )
        return record

    async def get_history(
        self,
        limit: int = 50,
        offset: int = 0,
        search: str | None = None,
    ) -> tuple[list[ToolExecution], int]:
        """
        Get paginated tool execution history.

        Returns tuple of (records, total_count).
        """
        query = select(ToolExecution)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    ToolExecution.tool_name.ilike(search_pattern),
                    ToolExecution.agent_name.ilike(search_pattern),
                    ToolExecution.result_summary.ilike(search_pattern),
                )
            )

        # Count query
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Data query
        query = query.order_by(ToolExecution.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        records = list(result.scalars().all())

        return records, total

    async def get_by_agent(self, agent_name: str) -> list[ToolExecution]:
        """Get all tool executions by a specific agent."""
        result = await self.db.execute(
            select(ToolExecution)
            .where(ToolExecution.agent_name == agent_name)
            .order_by(ToolExecution.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_tool(self, tool_name: str) -> list[ToolExecution]:
        """Get all executions of a specific tool."""
        result = await self.db.execute(
            select(ToolExecution)
            .where(ToolExecution.tool_name == tool_name)
            .order_by(ToolExecution.created_at.desc())
        )
        return list(result.scalars().all())
