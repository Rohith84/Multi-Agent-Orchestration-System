"""
Pydantic schemas for Analytics, LLM-as-a-Judge Evaluation, and Prompt Registry endpoints.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentMetricSchema(BaseModel):
    """Schema for a single agent execution metric."""

    id: str
    workflow_id: str
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

    id: str
    workflow_id: str
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

    id: str
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

    overall_quality_score: float
    total_workflows_executed: int
    total_tokens_consumed: int
    avg_workflow_latency: float
    success_rate_percentage: float
    model_stats: list[ModelPerformanceStats]
    tool_stats: list[ToolPerformanceStats]
    rag_stats: RAGPerformanceStats
    recent_agent_metrics: list[AgentMetricSchema]
