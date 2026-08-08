"""
Pydantic Schemas for AIOps: Model Registry, Routing, Benchmarks, Evaluations, Feedback, Quality Scores, Drift Reports, Optimizations, and Generic Pagination.
"""

from __future__ import annotations

import math
import uuid
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic Paginated API Response Wrapper."""

    items: list[T]
    total_records: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def create(cls, items: list[T], total_records: int, page: int, page_size: int) -> PaginatedResponse[T]:
        total_pages = math.ceil(total_records / page_size) if page_size > 0 else 0
        return cls(
            items=items,
            total_records=total_records,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class ModelRegistrySchema(BaseModel):
    """Schema for a registered model in the Centralized Model Registry."""

    id: uuid.UUID
    org_id: uuid.UUID
    model_name: str
    provider: str
    version: str
    is_local: bool
    capabilities: list[str]
    supported_languages: list[str]
    context_window: int
    supports_vision: bool
    supports_tool_calling: bool
    supports_json: bool
    avg_latency_ms: float
    avg_quality_score: float
    avg_token_usage: int
    avg_cost_per_1k: float
    availability: float
    health_status: str
    recommended_agent_roles: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateModelRequest(BaseModel):
    """Payload to register a new LLM model."""

    model_name: str = Field(..., description="Unique name of the model.")
    provider: str = Field(default="Ollama", description="Provider e.g. Ollama, OpenAI, Anthropic.")
    version: str = Field(default="1.0.0")
    is_local: bool = Field(default=True)
    capabilities: list[str] = Field(default_factory=lambda: ["reasoning", "coding", "chat"])
    supported_languages: list[str] = Field(default_factory=lambda: ["python", "typescript", "markdown"])
    context_window: int = Field(default=8192, ge=512)
    supports_vision: bool = Field(default=False)
    supports_tool_calling: bool = Field(default=True)
    supports_json: bool = Field(default=True)
    avg_latency_ms: float = Field(default=450.0, ge=0.0)
    avg_quality_score: float = Field(default=90.0, ge=0.0, le=100.0)
    avg_token_usage: int = Field(default=1200, ge=0)
    avg_cost_per_1k: float = Field(default=0.0, ge=0.0)
    availability: float = Field(default=99.9, ge=0.0, le=100.0)
    health_status: str = Field(default="HEALTHY")
    recommended_agent_roles: list[str] = Field(default_factory=lambda: ["Coder", "Planner"])


class ModelRoutingLogSchema(BaseModel):
    """Schema for model routing decisions."""

    id: uuid.UUID
    org_id: uuid.UUID
    workflow_run_id: str
    agent_role: str
    task_type: str
    reasoning_complexity: str
    selected_model: str
    fallback_model: str | None = None
    was_fallback_used: bool
    routing_reason: str
    latency_ms: float
    tokens_used: int
    estimated_cost: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteDecisionRequest(BaseModel):
    """Request payload to decide best model for task."""

    task_type: str = Field(..., description="e.g. code_synthesis, web_research, planning, vision_analysis")
    agent_role: str = Field(default="General")
    reasoning_complexity: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH")
    programming_language: str = Field(default="python")
    vision_required: bool = Field(default=False)
    document_size_kb: int = Field(default=10, ge=0)


class BenchmarkRunSchema(BaseModel):
    """Schema for automated benchmarks."""

    id: uuid.UUID
    org_id: uuid.UUID
    suite_name: str
    target_model: str
    target_prompt_version: str
    target_workflow: str
    accuracy_score: float
    latency_score: float
    cost_score: float
    overall_benchmark_score: float
    metrics_json: dict[str, Any]
    duration_ms: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RunBenchmarkRequest(BaseModel):
    """Payload to trigger benchmark run."""

    suite_name: str = Field(default="full_evaluation_suite")
    target_model: str = Field(default="qwen2.5-coder:7b")
    target_prompt_version: str = Field(default="v1.0")


class EvaluationReportSchema(BaseModel):
    """Schema for LLM agent evaluations."""

    id: uuid.UUID
    org_id: uuid.UUID
    workflow_run_id: str
    agent_role: str
    accuracy: float
    completeness: float
    correctness: float
    reasoning: float
    grounding: float
    hallucination_risk: float
    citation_quality: float
    code_quality: float
    safety: float
    overall_score: float
    summary: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateEvaluationRequest(BaseModel):
    """Payload to submit evaluation."""

    workflow_run_id: str
    agent_role: str
    accuracy: float = Field(default=92.0, ge=0.0, le=100.0)
    completeness: float = Field(default=90.0, ge=0.0, le=100.0)
    correctness: float = Field(default=95.0, ge=0.0, le=100.0)
    reasoning: float = Field(default=88.0, ge=0.0, le=100.0)
    grounding: float = Field(default=94.0, ge=0.0, le=100.0)
    hallucination_risk: float = Field(default=2.0, ge=0.0, le=100.0)
    citation_quality: float = Field(default=90.0, ge=0.0, le=100.0)
    code_quality: float = Field(default=95.0, ge=0.0, le=100.0)
    safety: float = Field(default=99.0, ge=0.0, le=100.0)
    summary: str = Field(default="High precision completion with solid safety.")


class FeedbackEventSchema(BaseModel):
    """Schema for user feedback events."""

    id: uuid.UUID
    org_id: uuid.UUID
    workflow_run_id: str
    user_id: str
    rating_type: str
    rating_score: float
    feedback_text: str
    workflow_satisfaction: float
    agent_satisfaction: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmitFeedbackRequest(BaseModel):
    """Payload to record user feedback."""

    workflow_run_id: str
    rating_type: str = Field(default="THUMBS", description="THUMBS, RATING_1_5, WRITTEN")
    rating_score: float = Field(default=5.0)
    feedback_text: str = Field(default="")
    workflow_satisfaction: float = Field(default=100.0, ge=0.0, le=100.0)
    agent_satisfaction: float = Field(default=100.0, ge=0.0, le=100.0)


class QualityScoreSchema(BaseModel):
    """Schema for unified Quality Score."""

    id: uuid.UUID
    org_id: uuid.UUID
    workflow_run_id: str
    unified_score: float
    accuracy_score: float
    latency_score: float
    token_efficiency_score: float
    retry_count: int
    tool_success_rate: float
    user_feedback_score: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DriftReportSchema(BaseModel):
    """Schema for drift detection reports."""

    id: uuid.UUID
    org_id: uuid.UUID
    drift_type: str
    target_identifier: str
    baseline_score: float
    current_score: float
    drift_delta: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OptimizationRecommendationSchema(BaseModel):
    """Schema for self-optimization recommendations."""

    id: uuid.UUID
    org_id: uuid.UUID
    category: str
    target_id: str
    recommended_action: str
    score_impact_estimate: float
    reasoning_summary: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
