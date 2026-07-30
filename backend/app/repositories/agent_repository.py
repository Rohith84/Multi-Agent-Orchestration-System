"""
AgentExecution repository — data access layer for recording agent run information.
"""

import uuid
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.agent_execution import AgentExecution

logger = get_logger(__name__)


class AgentExecutionRepository:
    """
    Handles persistence and query operations for AgentExecution records.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_execution(
        self,
        session_id: uuid.UUID,
        agent_name: str,
        input_content: str,
        output_content: str,
        execution_time: float,
        status: str,
    ) -> AgentExecution:
        """
        Save an agent execution record.
        """
        record = AgentExecution(
            session_id=session_id,
            agent_name=agent_name,
            input_content=input_content,
            output_content=output_content,
            execution_time=execution_time,
            status=status,
        )
        self.db.add(record)
        await self.db.flush()
        logger.debug(
            "Saved agent execution record for %s in session %s",
            agent_name,
            session_id,
        )
        return record

    async def get_session_executions(self, session_id: uuid.UUID) -> list[AgentExecution]:
        """
        Get all agent execution records for a session ordered chronologically.
        """
        result = await self.db.execute(
            select(AgentExecution)
            .where(AgentExecution.session_id == session_id)
            .order_by(AgentExecution.created_at.asc())
        )
        return list(result.scalars().all())

    async def delete_session_executions(self, session_id: uuid.UUID) -> int:
        """
        Delete all agent execution records for a session.
        """
        result = await self.db.execute(
            delete(AgentExecution).where(AgentExecution.session_id == session_id)
        )
        return result.rowcount
