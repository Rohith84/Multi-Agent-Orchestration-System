"""
Pydantic schemas for MCP tool API endpoints.

Defines request/response contracts for:
- GET /api/tools
- POST /api/tools/run
- GET /api/tools/history
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolParameterSchema(BaseModel):
    """Schema for a tool parameter definition."""
    type: str
    description: str


class ToolSchema(BaseModel):
    """Schema representing an available MCP tool."""
    name: str
    description: str
    category: str
    parameters: dict[str, Any]


class ToolListResponse(BaseModel):
    """Response from GET /api/tools."""
    tools: list[ToolSchema]
    count: int


class ToolRunRequest(BaseModel):
    """Request body for POST /api/tools/run."""
    tool_name: str = Field(
        ...,
        min_length=1,
        description="Name of the MCP tool to execute (e.g. 'filesystem.read_file').",
        examples=["filesystem.list_directory"],
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool.",
        examples=[{"path": "."}],
    )
    agent_name: str = Field(
        default="manual",
        description="Name of the agent invoking the tool, or 'manual' for direct API calls.",
    )


class ToolRunResponse(BaseModel):
    """Response from POST /api/tools/run."""
    success: bool
    tool_name: str
    result: Any = None
    error: str | None = None
    execution_time: float


class ToolExecutionSchema(BaseModel):
    """Schema for a tool execution history record."""
    id: str
    agent_name: str
    tool_name: str
    arguments: str
    status: str
    execution_time: float
    result_summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolHistoryResponse(BaseModel):
    """Response from GET /api/tools/history."""
    executions: list[ToolExecutionSchema]
    total: int
    limit: int
    offset: int
