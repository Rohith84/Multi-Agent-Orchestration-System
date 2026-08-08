"""
Enterprise AIOps API Router — Hardened Production Endpoints.

Enforces:
- Multi-tenant organization isolation (No fallback org IDs)
- RBAC Role checks (Platform Admin, Org Admin, Architect, Auditor, Developer)
- Pagination (page, page_size, total_records, total_pages)
- Dynamic Query Filtering & Sorting
- Comprehensive OpenAPI documentation and REST status codes
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.auth import get_current_user, require_role
from app.core.logging import get_logger
from app.services.aiops_service import AIOpsService
from app.services.model_router import IntelligentModelRouter
from app.services.evaluator import LLMEvaluator
from app.services.benchmark_engine import BenchmarkEngine
from app.schemas.aiops import (
    PaginatedResponse,
    ModelRegistrySchema,
    CreateModelRequest,
    ModelRoutingLogSchema,
    RouteDecisionRequest,
    EvaluationReportSchema,
    CreateEvaluationRequest,
    FeedbackEventSchema,
    SubmitFeedbackRequest,
    BenchmarkRunSchema,
    RunBenchmarkRequest,
    DriftReportSchema,
    OptimizationRecommendationSchema,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api", tags=["aiops"])


@router.get(
    "/models",
    response_model=PaginatedResponse[ModelRegistrySchema],
    summary="List Centralized Model Registry",
    description="Fetch paginated list of registered LLM models for authenticated organization with filtering and sorting.",
    status_code=status.HTTP_200_OK,
)
async def list_models(
    provider: str | None = Query(default=None, description="Filter by model provider e.g. Ollama, OpenAI"),
    health_status: str | None = Query(default=None, description="Filter by health status e.g. HEALTHY"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    sort_by: str = Query(default="avg_quality_score", description="Sort attribute"),
    sort_order: str = Query(default="desc", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse[ModelRegistrySchema]:
    """Get tenant-isolated, paginated model registry list."""
    service = AIOpsService(db)
    raw_org_id = user.get("org_id")
    items, total = await service.list_registered_models(
        raw_org_id=raw_org_id,
        provider=provider,
        health_status=health_status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    schemas = [ModelRegistrySchema.model_validate(m) for m in items]
    return PaginatedResponse.create(schemas, total_records=total, page=page, page_size=page_size)


@router.post(
    "/models",
    response_model=ModelRegistrySchema,
    summary="Register New LLM Model",
    description="Register a new LLM model in the Centralized Model Registry. Requires Platform Admin, Org Admin, or Architect role.",
    status_code=status.HTTP_201_CREATED,
)
async def register_model(
    request: CreateModelRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(require_role(["Platform Admin", "Organization Admin", "Architect"])),
) -> ModelRegistrySchema:
    """Register a model with explicit RBAC role verification."""
    service = AIOpsService(db)
    raw_org_id = user.get("org_id")
    model = await service.register_model(request, raw_org_id)
    return ModelRegistrySchema.model_validate(model)


@router.get(
    "/models/router",
    response_model=PaginatedResponse[ModelRoutingLogSchema],
    summary="List Intelligent Router Decision Logs",
    description="Fetch historical routing decisions and fallback execution logs.",
    status_code=status.HTTP_200_OK,
)
async def list_routing_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse[ModelRoutingLogSchema]:
    """Fetch paginated model routing logs."""
    router_service = IntelligentModelRouter(db)
    raw_org_id = user.get("org_id")
    logs, total = await router_service.list_recent_routing_logs(raw_org_id=raw_org_id, page=page, page_size=page_size)
    schemas = [ModelRoutingLogSchema.model_validate(l) for l in logs]
    return PaginatedResponse.create(schemas, total_records=total, page=page, page_size=page_size)


@router.post(
    "/models/router/decide",
    summary="Decide Intelligent Model Route",
    description="Intelligently route task to optimal LLM model and backup fallback based on complexity and latency metrics.",
    status_code=status.HTTP_200_OK,
)
async def decide_model_route(
    request: RouteDecisionRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Dynamically route request without hardcoded model selection."""
    router_service = IntelligentModelRouter(db)
    raw_org_id = user.get("org_id")
    return await router_service.select_best_model(request, raw_org_id)


@router.get(
    "/evaluations",
    response_model=PaginatedResponse[EvaluationReportSchema],
    summary="List LLM Evaluation Reports",
    description="Fetch paginated agent execution evaluations across accuracy, grounding, and code quality.",
    status_code=status.HTTP_200_OK,
)
async def list_evaluations(
    agent_role: str | None = Query(default=None, description="Filter by agent role e.g. Coder, Planner"),
    workflow_run_id: str | None = Query(default=None, description="Filter by workflow run ID"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse[EvaluationReportSchema]:
    """Fetch paginated evaluation reports."""
    service = AIOpsService(db)
    raw_org_id = user.get("org_id")
    reports, total = await service.list_evaluations(
        raw_org_id=raw_org_id,
        agent_role=agent_role,
        workflow_run_id=workflow_run_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    schemas = [EvaluationReportSchema.model_validate(r) for r in reports]
    return PaginatedResponse.create(schemas, total_records=total, page=page, page_size=page_size)


@router.post(
    "/evaluations",
    response_model=EvaluationReportSchema,
    summary="Submit Structured LLM Agent Evaluation",
    description="Record structured evaluation metrics for agent workflow execution. Requires Developer, Reviewer, or Admin role.",
    status_code=status.HTTP_201_CREATED,
)
async def create_evaluation(
    request: CreateEvaluationRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(require_role(["Platform Admin", "Organization Admin", "Architect", "Reviewer", "Developer"])),
) -> EvaluationReportSchema:
    """Submit evaluation with RBAC enforcement."""
    evaluator = LLMEvaluator(db)
    raw_org_id = user.get("org_id")
    report = await evaluator.evaluate_agent_output(request, raw_org_id)
    return EvaluationReportSchema.model_validate(report)


@router.post(
    "/feedback",
    response_model=FeedbackEventSchema,
    summary="Submit User Feedback",
    description="Collect user satisfaction feedback and update Quality Scores.",
    status_code=status.HTTP_201_CREATED,
)
async def submit_user_feedback(
    request: SubmitFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> FeedbackEventSchema:
    """Record user feedback."""
    service = AIOpsService(db)
    raw_org_id = user.get("org_id")
    user_id = user.get("user_id", "user_authenticated")
    event = await service.record_feedback(request, raw_org_id, user_id)
    return FeedbackEventSchema.model_validate(event)


@router.get(
    "/benchmarks",
    response_model=PaginatedResponse[BenchmarkRunSchema],
    summary="List Automated Benchmark Runs",
    description="Fetch benchmark history comparing models, prompt versions, and workflows.",
    status_code=status.HTTP_200_OK,
)
async def list_benchmarks(
    target_model: str | None = Query(default=None, description="Filter by target model name"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse[BenchmarkRunSchema]:
    """Fetch paginated benchmark run history."""
    engine = BenchmarkEngine(db)
    raw_org_id = user.get("org_id")
    runs, total = await engine.list_benchmark_runs(raw_org_id=raw_org_id, target_model=target_model, page=page, page_size=page_size)
    schemas = [BenchmarkRunSchema.model_validate(r) for r in runs]
    return PaginatedResponse.create(schemas, total_records=total, page=page, page_size=page_size)


@router.post(
    "/benchmarks/run",
    response_model=BenchmarkRunSchema,
    summary="Trigger Automated Benchmark Suite",
    description="Trigger automated benchmark suite for a model. Requires Platform Admin, Org Admin, or Architect role.",
    status_code=status.HTTP_201_CREATED,
)
async def run_benchmark_suite(
    request: RunBenchmarkRequest,
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(require_role(["Platform Admin", "Organization Admin", "Architect"])),
) -> BenchmarkRunSchema:
    """Trigger benchmark with RBAC enforcement."""
    engine = BenchmarkEngine(db)
    raw_org_id = user.get("org_id")
    run = await engine.execute_benchmark(request, raw_org_id)
    return BenchmarkRunSchema.model_validate(run)


@router.get(
    "/drift",
    response_model=PaginatedResponse[DriftReportSchema],
    summary="List Drift Detection Reports",
    description="Fetch drift detection alerts across models, prompts, knowledge bases, and embeddings.",
    status_code=status.HTTP_200_OK,
)
async def list_drift_reports(
    drift_type: str | None = Query(default=None, description="Filter by drift type: MODEL, PROMPT, KNOWLEDGE_BASE"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status: NORMAL, WARNING, ALERT"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse[DriftReportSchema]:
    """Fetch paginated drift detection logs."""
    service = AIOpsService(db)
    raw_org_id = user.get("org_id")
    reports, total = await service.list_drift_reports(
        raw_org_id=raw_org_id,
        drift_type=drift_type,
        status_filter=status_filter,
        page=page,
        page_size=page_size,
    )
    schemas = [DriftReportSchema.model_validate(r) for r in reports]
    return PaginatedResponse.create(schemas, total_records=total, page=page, page_size=page_size)


@router.get(
    "/optimizations",
    response_model=PaginatedResponse[OptimizationRecommendationSchema],
    summary="List Self-Optimization Recommendations",
    description="Fetch non-mutating self-optimization recommendations for models, prompts, and workflows.",
    status_code=status.HTTP_200_OK,
)
async def list_optimization_recommendations(
    category: str | None = Query(default=None, description="Filter by category e.g. MODEL_SELECTION, PROMPT_OPTIMIZATION"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse[OptimizationRecommendationSchema]:
    """Fetch paginated self-optimization recommendations."""
    service = AIOpsService(db)
    raw_org_id = user.get("org_id")
    recs, total = await service.list_recommendations(
        raw_org_id=raw_org_id,
        category=category,
        page=page,
        page_size=page_size,
    )
    schemas = [OptimizationRecommendationSchema.model_validate(r) for r in recs]
    return PaginatedResponse.create(schemas, total_records=total, page=page, page_size=page_size)
