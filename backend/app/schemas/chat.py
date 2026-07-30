"""
Pydantic schemas for chat API endpoints.

Defines request/response contracts for:
- POST /api/chat
- GET /api/chat/{session_id}
- DELETE /api/chat/{session_id}
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Request body for POST /api/chat."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="The user message to send to the AI assistant.",
        examples=["Explain FastAPI in simple terms."],
    )
    session_id: str | None = Field(
        default=None,
        description="Optional session ID to continue an existing conversation. If omitted, a new session is created.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )


class ChatResponse(BaseModel):
    """Response from POST /api/chat."""

    response: str = Field(
        ...,
        description="The AI assistant's response.",
    )
    session_id: str = Field(
        ...,
        description="The session ID for this conversation.",
    )
    model_name: str = Field(
        ...,
        alias="model",
        serialization_alias="model",
        description="The model that generated this response.",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp of the response.",
    )

    model_config = ConfigDict(populate_by_name=True)


class ChatMessageSchema(BaseModel):
    """Schema for a single chat message in history."""

    id: str
    session_id: str
    role: str
    message: str
    llm_model: str | None = Field(default=None, alias="model", serialization_alias="model")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ChatHistoryResponse(BaseModel):
    """Response from GET /api/chat/{session_id}."""

    session_id: str
    messages: list[ChatMessageSchema]
    message_count: int


class ChatDeleteResponse(BaseModel):
    """Response from DELETE /api/chat/{session_id}."""

    message: str
    session_id: str
    deleted_count: int
