"""
Workflow Management API Endpoints.

Provides:
- GET /api/workflows — list workflows
- GET /api/workflows/{id} — detailed view of workflow, checkpoints, approvals
- POST /api/workflows/chat — start workflow execution stream
- POST /api/workflows/{id}/approve — approve pending approval gate and resume stream
- POST /api/workflows/{id}/reject — reject pending approval gate
- POST /api/workflows/{id}/resume — resume paused or failed workflow stream
- POST /api/workflows/{id}/cancel — cancel workflow
- POST /api/workflows/{id}/restart — restart workflow from START
- POST /api/workflows/schedule — create scheduled workflow
- GET /api/workflows/schedules — list active schedules
"""

from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.logging import get_logger
from app.schemas.workflows import (
    WorkflowStartRequest,
    WorkflowApprovalDecision,
    WorkflowScheduleRequest,
    WorkflowListResponse,
    WorkflowDetailSchema,
    WorkflowScheduleListResponse,
    WorkflowScheduleSchema,
)
from app.services.workflow_service import WorkflowService
from app.orchestration.workflow import WorkflowExecutor

logger = get_logger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _get_workflow_service(db: AsyncSession = Depends(get_db)) -> WorkflowService:
    return WorkflowService(db)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowListResponse:
    """List workflows with pagination."""
    return await service.list_workflows(limit=limit, offset=offset)


@router.get("/schedules", response_model=WorkflowScheduleListResponse)
async def list_schedules(
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowScheduleListResponse:
    """List workflow schedules."""
    return await service.list_schedules()


@router.post("/schedule", response_model=WorkflowScheduleSchema)
async def create_schedule(
    request: WorkflowScheduleRequest,
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowScheduleSchema:
    """Schedule a workflow execution."""
    return await service.create_schedule(
        title=request.title,
        message=request.message,
        cron_expression=request.cron_expression,
        require_approval_agents=request.require_approval_agents,
    )


@router.get("/{workflow_id}", response_model=WorkflowDetailSchema)
async def get_workflow_detail(
    workflow_id: str,
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowDetailSchema:
    """Get detailed state of a workflow including checkpoints and approvals."""
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    detail = await service.get_workflow_detail(wid)
    if not detail:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return detail


@router.post("/chat")
async def start_workflow_chat(
    request: WorkflowStartRequest,
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Start a workflow execution stream with optional human approval requirement.
    """
    session_id = uuid.UUID(request.session_id) if request.session_id else uuid.uuid4()
    executor = WorkflowExecutor(db)

    return StreamingResponse(
        executor.execute(
            user_request=request.message,
            session_id=session_id,
            require_approval_agents=request.require_approval_agents,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{workflow_id}/approve")
async def approve_workflow(
    workflow_id: str,
    decision: WorkflowApprovalDecision,
    db: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(_get_workflow_service),
) -> StreamingResponse:
    """
    Approve a pending approval gate and resume execution via SSE streaming.
    """
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    detail = await service.get_workflow_detail(wid)
    if not detail:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Approve decision in DB
    try:
        await service.approve_workflow_stage(wid, comments=decision.comments)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    executor = WorkflowExecutor(db)
    session_id = uuid.UUID(detail.session_id)

    return StreamingResponse(
        executor.execute(
            user_request=detail.user_request,
            session_id=session_id,
            require_approval_agents=detail.require_approval_agents,
            workflow_id=wid,
            resume_agent=detail.current_agent,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{workflow_id}/reject")
async def reject_workflow(
    workflow_id: str,
    decision: WorkflowApprovalDecision,
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowDetailSchema:
    """
    Reject a pending approval gate and cancel workflow execution.
    """
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    try:
        res = await service.reject_workflow_stage(wid, comments=decision.comments)
        if not res:
            raise HTTPException(status_code=404, detail="Workflow not found")
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: str,
    db: AsyncSession = Depends(get_db),
    service: WorkflowService = Depends(_get_workflow_service),
) -> StreamingResponse:
    """
    Resume a paused or failed workflow from its latest checkpoint.
    """
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    detail = await service.get_workflow_detail(wid)
    if not detail:
        raise HTTPException(status_code=404, detail="Workflow not found")

    executor = WorkflowExecutor(db)
    session_id = uuid.UUID(detail.session_id)

    return StreamingResponse(
        executor.execute(
            user_request=detail.user_request,
            session_id=session_id,
            require_approval_agents=detail.require_approval_agents,
            workflow_id=wid,
            resume_agent=detail.current_agent,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowDetailSchema:
    """Cancel workflow execution."""
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    res = await service.cancel_workflow(wid)
    if not res:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return res


@router.post("/{workflow_id}/restart")
async def restart_workflow(
    workflow_id: str,
    service: WorkflowService = Depends(_get_workflow_service),
) -> WorkflowDetailSchema:
    """Restart workflow execution from START."""
    try:
        wid = uuid.UUID(workflow_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")

    res = await service.restart_workflow(wid)
    if not res:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return res
