"""
AIOps SQLAlchemy Models: Model Registry, Routing, Benchmarks, Evaluations, Feedback, Quality Scores, Drift Reports, and Optimization Recommendations.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, Uuid, func, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ModelRegistryItem(Base):
    """
    Centralized Model Registry tracking model capabilities, metrics, and health status.
    """

    __tablename__ = "model_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )
    provider: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="Ollama",
    )
    version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="1.0.0",
    )
    is_local: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    capabilities: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    supported_languages: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    context_window: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=8192,
    )
    supports_vision: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    supports_tool_calling: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    supports_json: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    avg_latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=450.0,
    )
    avg_quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=92.5,
    )
    avg_token_usage: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1200,
    )
    avg_cost_per_1k: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    availability: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=99.9,
    )
    health_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="HEALTHY",
    )
    recommended_agent_roles: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ModelRegistryItem(model_name='{self.model_name}', provider='{self.provider}', health='{self.health_status}')>"


class ModelRoutingLog(Base):
    """
    Intelligent Model Routing execution logs and fallback telemetry.
    """

    __tablename__ = "model_routing"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    agent_role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    task_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    reasoning_complexity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="MEDIUM",
    )
    selected_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    fallback_model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    was_fallback_used: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    routing_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    latency_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    estimated_cost: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<ModelRoutingLog(task='{self.task_type}', model='{self.selected_model}', fallback={self.was_fallback_used})>"


class BenchmarkRun(Base):
    """
    Automated evaluation and benchmark suite runs.
    """

    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    suite_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_model: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    target_prompt_version: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="v1.0",
    )
    target_workflow: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="standard_pipeline",
    )
    accuracy_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    latency_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    cost_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    overall_benchmark_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    metrics_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    duration_ms: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<BenchmarkRun(suite='{self.suite_name}', model='{self.target_model}', score={self.overall_benchmark_score})>"


class EvaluationReport(Base):
    """
    Automated LLM Agent evaluation reports.
    """

    __tablename__ = "evaluation_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    agent_role: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    accuracy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=90.0,
    )
    completeness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=92.0,
    )
    correctness: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=95.0,
    )
    reasoning: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=88.0,
    )
    grounding: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=94.0,
    )
    hallucination_risk: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=3.5,
    )
    citation_quality: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=91.0,
    )
    code_quality: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=93.0,
    )
    safety: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=99.0,
    )
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=92.0,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EvaluationReport(workflow='{self.workflow_run_id}', agent='{self.agent_role}', score={self.overall_score})>"


class FeedbackEvent(Base):
    """
    User feedback event on workflow / agent executions.
    """

    __tablename__ = "feedback_events"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="admin",
    )
    rating_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="THUMBS",
    )  # THUMBS, RATING_1_5, WRITTEN
    rating_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=5.0,
    )
    feedback_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    workflow_satisfaction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )
    agent_satisfaction: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FeedbackEvent(workflow='{self.workflow_run_id}', rating={self.rating_score})>"


class QualityScoreItem(Base):
    """
    Unified Quality Score tracking for workflows and models.
    """

    __tablename__ = "quality_scores"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    workflow_run_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    unified_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=95.0,
    )
    accuracy_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=95.0,
    )
    latency_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=90.0,
    )
    token_efficiency_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=92.0,
    )
    retry_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    tool_success_rate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=100.0,
    )
    user_feedback_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=95.0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<QualityScoreItem(workflow='{self.workflow_run_id}', unified_score={self.unified_score})>"


class DriftReportItem(Base):
    """
    Drift detection report for Model, Prompt, Knowledge Base, Workflow, and Embeddings.
    """

    __tablename__ = "drift_reports"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    drift_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )  # MODEL, PROMPT, KNOWLEDGE_BASE, WORKFLOW, EMBEDDING
    target_identifier: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    baseline_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=95.0,
    )
    current_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=88.0,
    )
    drift_delta: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=-7.0,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="ALERT",
    )  # NORMAL, WARNING, ALERT
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<DriftReportItem(type='{self.drift_type}', target='{self.target_identifier}', delta={self.drift_delta})>"


class OptimizationRecommendation(Base):
    """
    Non-mutating self-optimization recommendations.
    """

    __tablename__ = "optimization_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )  # MODEL_SELECTION, PROMPT_OPTIMIZATION, WORKFLOW_PARALLELIZATION, KNOWLEDGE_CLEANUP, PROMPT_REFACTORING
    target_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    recommended_action: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    score_impact_estimate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=+5.0,
    )
    reasoning_summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="PENDING_REVIEW",
    )  # PENDING_REVIEW, APPLIED, DISMISSED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<OptimizationRecommendation(category='{self.category}', target='{self.target_id}')>"
