"""
Chat service — business logic for AI chat conversations.

Orchestrates the flow between the repository (data layer)
and the OllamaClient (AI layer) to provide a complete
chat experience with persistent history.
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.ollama_client import OllamaClient
from app.core.config import get_settings
from app.core.exceptions import ChatSessionNotFoundError
from app.core.logging import get_logger
from app.models.chat import ChatMessage
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import (
    ChatDeleteResponse,
    ChatHistoryResponse,
    ChatMessageSchema,
    ChatResponse,
)

logger = get_logger(__name__)


class ChatService:
    """
    Service layer for chat operations.

    Coordinates between:
    - ChatRepository: persisting messages to PostgreSQL
    - OllamaClient: generating AI responses via Ollama
    - Settings: system prompt and model configuration
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repository = ChatRepository(db)
        self.ollama = OllamaClient()
        self.settings = get_settings()

    async def send_message(self, user_message: str, session_id: str | None = None) -> ChatResponse:
        """
        Process a user message and return the AI response.

        Flow:
        1. Generate or validate session_id
        2. Load existing conversation history
        3. Store user message
        4. Build messages array (system + history + new message)
        5. Call Ollama for response
        6. Store assistant response
        7. Return structured response

        Args:
            user_message: The user's input message.
            session_id: Optional existing session ID to continue.

        Returns:
            ChatResponse with the AI response and metadata.
        """
        # Step 1: Resolve session ID
        sid = uuid.UUID(session_id) if session_id else uuid.uuid4()
        logger.info("Processing chat message for session %s", sid)

        # Step 2: Load existing history
        history = await self.repository.get_history(sid)

        # Step 3: Store user message
        await self.repository.save_message(
            session_id=sid,
            role="user",
            message=user_message,
            model=None,
        )

        # Step 4: Build messages array for Ollama
        messages = self._build_messages(history, user_message)

        # Step 5: Call Ollama with explain model if configured
        model_to_use = self.settings.model_explain or self.settings.model_name
        ai_response = await self.ollama.chat(messages, model=model_to_use)

        # Step 6: Store assistant response
        assistant_msg = await self.repository.save_message(
            session_id=sid,
            role="assistant",
            message=ai_response,
            model=model_to_use,
        )

        logger.info("Chat completed for session %s", sid)

        # Step 7: Return response
        return ChatResponse(
            response=ai_response,
            session_id=str(sid),
            model_name=self.settings.model_name,
            created_at=assistant_msg.created_at,
        )

    async def get_history(self, session_id: str) -> ChatHistoryResponse:
        """
        Retrieve the full conversation history for a session.

        Args:
            session_id: The session to retrieve.

        Returns:
            ChatHistoryResponse with all messages.

        Raises:
            ChatSessionNotFoundError: If the session does not exist.
        """
        sid = uuid.UUID(session_id)

        exists = await self.repository.session_exists(sid)
        if not exists:
            raise ChatSessionNotFoundError(session_id)

        history = await self.repository.get_history(sid)

        return ChatHistoryResponse(
            session_id=session_id,
            messages=[
                ChatMessageSchema(
                    id=str(msg.id),
                    session_id=str(msg.session_id),
                    role=msg.role,
                    message=msg.message,
                    llm_model=msg.model,
                    created_at=msg.created_at,
                )
                for msg in history
            ],
            message_count=len(history),
        )

    async def delete_session(self, session_id: str) -> ChatDeleteResponse:
        """
        Delete all messages for a conversation session.

        Args:
            session_id: The session to delete.

        Returns:
            ChatDeleteResponse with deletion details.

        Raises:
            ChatSessionNotFoundError: If the session does not exist.
        """
        sid = uuid.UUID(session_id)

        exists = await self.repository.session_exists(sid)
        if not exists:
            raise ChatSessionNotFoundError(session_id)

        deleted_count = await self.repository.delete_session(sid)

        logger.info("Deleted session %s (%d messages)", session_id, deleted_count)

        return ChatDeleteResponse(
            message="Chat session deleted successfully.",
            session_id=session_id,
            deleted_count=deleted_count,
        )

    def _build_messages(
        self,
        history: list[ChatMessage],
        new_user_message: str,
    ) -> list[dict[str, str]]:
        """
        Build the messages array to send to Ollama.

        Includes system prompt, conversation history,
        and the new user message.

        Args:
            history: Previous messages in the session.
            new_user_message: The latest user message.

        Returns:
            List of message dicts for the Ollama API.
        """
        messages: list[dict[str, str]] = []

        # System prompt — always first
        messages.append({
            "role": "system",
            "content": self.settings.ask_system_prompt,
        })

        # Historical messages (excluding system prompts from DB)
        for msg in history:
            if msg.role in ("user", "assistant"):
                messages.append({
                    "role": msg.role,
                    "content": msg.message,
                })

        # New user message
        messages.append({
            "role": "user",
            "content": new_user_message,
        })

        return messages
