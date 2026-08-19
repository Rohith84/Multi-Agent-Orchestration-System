"""
Pydantic schemas for the Multi-Agent orchestrator endpoints.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.chat import ChatMessageSchema


class AgentRequest(BaseModel):
    """Request structure for starting a multi-agent chat."""
    message: str = Field(..., min_length=1)
    session_id: str | None = Field(default=None)
    require_approval_agents: list[str] = Field(default_factory=list)


class AgentExecutionSchema(BaseModel):
    """Schema representing an individual agent run inside history."""
    id: str
    session_id: str
    agent_name: str
    input_content: str
    output_content: str
    execution_time: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentHistoryResponse(BaseModel):
    """Aggregated workflow execution history response."""
    session_id: str
    chat_history: list[ChatMessageSchema]
    agent_executions: list[AgentExecutionSchema]
    execution_order: list[str]
