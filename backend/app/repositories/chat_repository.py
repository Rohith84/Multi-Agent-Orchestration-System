"""
Chat repository — data access layer for chat messages.

Provides CRUD operations for ChatMessage model.
All methods accept an AsyncSession via dependency injection.
"""

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.chat import ChatMessage

logger = get_logger(__name__)


class ChatRepository:
    """
    Repository for ChatMessage CRUD operations.

    Follows the Repository pattern to separate data access
    from business logic. Each method operates within the
    session provided by the caller.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save_message(
        self,
        session_id: uuid.UUID,
        role: str,
        message: str,
        model: str | None = None,
    ) -> ChatMessage:
        """
        Save a chat message to the database.

        Args:
            session_id: Conversation session identifier.
            role: Message role ('system', 'user', 'assistant').
            message: The message content.
            model: The LLM model name (for assistant messages).

        Returns:
            The saved ChatMessage instance.
        """
        chat_message = ChatMessage(
            session_id=session_id,
            role=role,
            message=message,
            model=model,
        )
        self.db.add(chat_message)
        await self.db.flush()
        logger.debug(
            "Saved %s message for session %s (id=%s)",
            role,
            session_id,
            chat_message.id,
        )
        return chat_message

    async def get_history(self, session_id: uuid.UUID) -> list[ChatMessage]:
        """
        Retrieve all messages for a session, ordered by creation time.

        Args:
            session_id: The conversation session to retrieve.

        Returns:
            List of ChatMessage objects in chronological order.
        """
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = list(result.scalars().all())
        logger.debug(
            "Retrieved %d messages for session %s",
            len(messages),
            session_id,
        )
        return messages

    async def delete_session(self, session_id: uuid.UUID) -> int:
        """
        Delete all messages for a session.

        Args:
            session_id: The conversation session to delete.

        Returns:
            Number of messages deleted.
        """
        result = await self.db.execute(
            delete(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        deleted_count = result.rowcount
        logger.info(
            "Deleted %d messages for session %s",
            deleted_count,
            session_id,
        )
        return deleted_count

    async def session_exists(self, session_id: uuid.UUID) -> bool:
        """
        Check if a session has any messages.

        Args:
            session_id: The session to check.

        Returns:
            True if the session exists, False otherwise.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.session_id == session_id)
        )
        count = result.scalar_one()
        return count > 0
