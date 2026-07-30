"""
Chat API endpoints.

Provides:
- POST /api/chat          — send a message and get an AI response
- GET  /api/chat/{id}     — retrieve conversation history
- DELETE /api/chat/{id}   — delete a conversation session
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db
from app.schemas.chat import (
    ChatDeleteResponse,
    ChatHistoryResponse,
    ChatRequest,
    ChatResponse,
)
from app.services.chat_service import ChatService

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])


def _get_chat_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    """Dependency that provides a ChatService instance."""
    return ChatService(db)


@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    service: ChatService = Depends(_get_chat_service),
) -> ChatResponse:
    """
    Send a message to the AI assistant.

    Creates a new conversation session if session_id is not provided.
    Returns the AI response with the session_id for follow-up messages.
    """
    logger.info("POST /api/chat — message length=%d", len(request.message))
    return await service.send_message(
        user_message=request.message,
        session_id=request.session_id,
    )


@router.get("/chat/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str,
    service: ChatService = Depends(_get_chat_service),
) -> ChatHistoryResponse:
    """
    Retrieve the full conversation history for a session.

    Returns all messages in chronological order.
    """
    logger.info("GET /api/chat/%s", session_id)
    return await service.get_history(session_id)


@router.delete("/chat/{session_id}", response_model=ChatDeleteResponse)
async def delete_chat_session(
    session_id: str,
    service: ChatService = Depends(_get_chat_service),
) -> ChatDeleteResponse:
    """
    Delete a conversation session and all its messages.

    This action is irreversible.
    """
    logger.info("DELETE /api/chat/%s", session_id)
    return await service.delete_session(session_id)
