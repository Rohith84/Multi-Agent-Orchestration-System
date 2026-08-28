"""
Pydantic schemas for Analytics, LLM-as-a-Judge Evaluation, and Prompt Registry endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentMetricSchema(BaseModel):
    """Schema for a single agent execution metric."""

    id: uuid.UUID
    workflow_id: uuid.UUID
    agent_name: str
    model: str
    start_time: datetime
    end_time: datetime
    duration: float
    input_tokens: int
    output_tokens: int
    total_tokens: int
    status: str
    retry_count: int
    tool_calls: int
    knowledge_chunks: int
    score: float
    eval_breakdown: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkflowMetricSchema(BaseModel):
    """Schema for workflow aggregated metrics."""

    id: uuid.UUID
    workflow_id: uuid.UUID
    total_duration: float
    total_tokens: int
    approval_wait_time: float
    tool_execution_time: float
    rag_time: float
    overall_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptVersionSchema(BaseModel):
    """Schema for prompt versioning entry."""

    id: uuid.UUID
    agent_name: str
    version: str
    template: str
    description: str
    active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptCreateRequest(BaseModel):
    """Request to create a new prompt version."""

    agent_name: str = Field(..., description="Agent name: planner, research, coder, tester, reviewer")
    version: str = Field(..., description="Version identifier, e.g. v2.0")
    template: str = Field(..., description="Full system prompt template")
    description: str = Field(default="", description="Change summary or description")


class ModelPerformanceStats(BaseModel):
    """Comparative stats by model."""

    model_name: str
    total_calls: int
    avg_duration: float
    avg_tokens: float
    avg_score: float
    success_rate: float


class ToolPerformanceStats(BaseModel):
    """MCP Tool analytics."""

    tool_name: str
    category: str
    total_calls: int
    avg_duration: float
    success_rate: float
    failure_count: int


class RAGPerformanceStats(BaseModel):
    """RAG Retrieval analytics."""

    total_queries: int
    avg_retrieval_latency: float
    avg_similarity_score: float
    total_chunks_retrieved: int


class DashboardAnalyticsResponse(BaseModel):
    """Complete system observability and analytics dashboard response."""

    overall_quality_score: float | None = None
    total_workflows_executed: int
    total_tokens_consumed: int | None = None
    avg_workflow_latency: float | None = None
    success_rate_percentage: float | None = None
    model_stats: list[ModelPerformanceStats]
    tool_stats: list[ToolPerformanceStats]
    rag_stats: RAGPerformanceStats | None = None
    recent_agent_metrics: list[AgentMetricSchema]
    token_usage_available: bool = False
    rag_metrics_available: bool = False
