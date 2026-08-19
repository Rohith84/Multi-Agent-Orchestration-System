"""
WorkflowService — Business logic layer for Workflows, Checkpointing, Approvals, and Scheduling.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.repositories.workflow_repository import WorkflowRepository
from app.schemas.workflows import (
    WorkflowSchema,
    WorkflowDetailSchema,
    WorkflowCheckpointSchema,
    WorkflowApprovalSchema,
    WorkflowListResponse,
    WorkflowScheduleSchema,
    WorkflowScheduleListResponse,
)

logger = get_logger(__name__)


class WorkflowService:
    """
    Service coordinating workflow queries, approvals, checkpoint retrievals, and schedules.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = WorkflowRepository(db)

    async def list_workflows(self, limit: int = 50, offset: int = 0) -> WorkflowListResponse:
        """List workflows with pagination."""
        workflows, total = await self.repo.list_workflows(limit=limit, offset=offset)
        return WorkflowListResponse(
            workflows=[WorkflowSchema.model_validate(w) for w in workflows],
            total=total,
        )

    async def get_workflow_detail(self, workflow_id: uuid.UUID) -> WorkflowDetailSchema | None:
        """Get workflow detail including checkpoints and approval requests."""
        workflow = await self.repo.get_workflow(workflow_id)
        if not workflow:
            return None

        checkpoints = await self.repo.get_checkpoints(workflow_id)
        approvals = await self.repo.get_approvals(workflow_id)

        detail = WorkflowDetailSchema.model_validate(workflow)
        detail.checkpoints = [WorkflowCheckpointSchema.model_validate(c) for c in checkpoints]
        detail.approvals = [WorkflowApprovalSchema.model_validate(a) for a in approvals]
        return detail

    async def approve_workflow_stage(
        self,
        workflow_id: uuid.UUID,
        comments: str | None = None,
    ) -> WorkflowDetailSchema | None:
        """Approve a pending workflow approval gate."""
        approval = await self.repo.get_pending_approval(workflow_id)
        if not approval:
            raise ValueError(f"No pending approval request for workflow {workflow_id}")

        await self.repo.update_approval(approval.id, status="approved", comments=comments)
        await self.repo.update_workflow(workflow_id, status="running")
        await self.db.commit()

        logger.info("Workflow %s stage %s APPROVED", workflow_id, approval.agent_name)
        return await self.get_workflow_detail(workflow_id)

    async def reject_workflow_stage(
        self,
        workflow_id: uuid.UUID,
        comments: str | None = None,
    ) -> WorkflowDetailSchema | None:
        """Reject a pending workflow approval gate."""
        approval = await self.repo.get_pending_approval(workflow_id)
        if not approval:
            raise ValueError(f"No pending approval request for workflow {workflow_id}")

        await self.repo.update_approval(approval.id, status="rejected", comments=comments)
        await self.repo.update_workflow(workflow_id, status="cancelled", error_message=f"Rejected at agent {approval.agent_name}")
        await self.db.commit()

        logger.info("Workflow %s stage %s REJECTED", workflow_id, approval.agent_name)
        return await self.get_workflow_detail(workflow_id)

    async def cancel_workflow(self, workflow_id: uuid.UUID) -> WorkflowDetailSchema | None:
        """Cancel a running or paused workflow."""
        workflow = await self.repo.update_workflow(
            workflow_id,
            status="cancelled",
            error_message="Workflow cancelled by user",
        )
        if not workflow:
            return None
        await self.db.commit()
        return await self.get_workflow_detail(workflow_id)

    async def restart_workflow(self, workflow_id: uuid.UUID) -> WorkflowDetailSchema | None:
        """Restart a workflow from the beginning."""
        await self.repo.clear_execution_state(workflow_id)
        workflow = await self.repo.update_workflow(
            workflow_id,
            status="pending",
            current_agent="planner",
            progress_percentage=0,
            execution_time=0.0,
            error_message=None,
        )
        if not workflow:
            return None
        await self.db.commit()
        return await self.get_workflow_detail(workflow_id)

    async def create_schedule(
        self,
        title: str,
        message: str,
        cron_expression: str = "0 0 * * *",
        require_approval_agents: list[str] | None = None,
    ) -> WorkflowScheduleSchema:
        """Create a workflow schedule."""
        sched = await self.repo.create_schedule(
            title=title,
            user_request=message,
            cron_expression=cron_expression,
            require_approval_agents=require_approval_agents,
        )
        await self.db.commit()
        return WorkflowScheduleSchema.model_validate(sched)

    async def list_schedules(self) -> WorkflowScheduleListResponse:
        """List active schedules."""
        schedules = await self.repo.list_schedules()
        return WorkflowScheduleListResponse(
            schedules=[WorkflowScheduleSchema.model_validate(s) for s in schedules],
            total=len(schedules),
        )
