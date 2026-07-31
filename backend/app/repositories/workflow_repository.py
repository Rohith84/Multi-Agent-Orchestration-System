"""
WorkflowRepository — data access layer for Workflows, Checkpoints, Approvals, Schedules, and Planning Memories.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import select, update, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.workflow import (
    Workflow,
    WorkflowCheckpoint,
    WorkflowApproval,
    PlanningMemory,
    WorkflowSchedule,
)

logger = get_logger(__name__)


class WorkflowRepository:
    """
    Handles database persistence for workflows, checkpoints, approvals, schedules, and planning memories.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # --- Workflows ---

    async def create_workflow(
        self,
        session_id: uuid.UUID,
        user_request: str,
        title: str | None = None,
        require_approval_agents: list[str] | None = None,
    ) -> Workflow:
        """Create a new workflow record."""
        workflow = Workflow(
            session_id=session_id,
            title=title or f"Workflow: {user_request[:40]}...",
            user_request=user_request,
            status="pending",
            current_agent="planner",
            progress_percentage=0,
            require_approval_agents=require_approval_agents or [],
        )
        self.db.add(workflow)
        await self.db.flush()
        logger.info("Created workflow record ID=%s", workflow.id)
        return workflow

    async def get_workflow(self, workflow_id: uuid.UUID) -> Workflow | None:
        """Retrieve workflow by ID."""
        result = await self.db.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        return result.scalar_one_or_none()

    async def get_workflow_by_session(self, session_id: uuid.UUID) -> Workflow | None:
        """Retrieve most recent workflow by session ID."""
        result = await self.db.execute(
            select(Workflow)
            .where(Workflow.session_id == session_id)
            .order_by(Workflow.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_workflows(self, limit: int = 50, offset: int = 0) -> tuple[list[Workflow], int]:
        """List workflows paginated."""
        count_res = await self.db.execute(select(func.count(Workflow.id)))
        total = count_res.scalar() or 0

        res = await self.db.execute(
            select(Workflow)
            .order_by(Workflow.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        workflows = list(res.scalars().all())
        return workflows, total

    async def update_workflow(
        self,
        workflow_id: uuid.UUID,
        status: str | None = None,
        current_agent: str | None = None,
        progress_percentage: int | None = None,
        execution_time: float | None = None,
        error_message: str | None = None,
    ) -> Workflow | None:
        """Update workflow execution state."""
        workflow = await self.get_workflow(workflow_id)
        if not workflow:
            return None

        if status is not None:
            workflow.status = status
        if current_agent is not None:
            workflow.current_agent = current_agent
        if progress_percentage is not None:
            workflow.progress_percentage = progress_percentage
        if execution_time is not None:
            workflow.execution_time = execution_time
        if error_message is not None:
            workflow.error_message = error_message

        workflow.updated_at = datetime.utcnow()
        await self.db.flush()
        return workflow

    # --- Checkpoints ---

    async def save_checkpoint(
        self,
        workflow_id: uuid.UUID,
        agent_name: str,
        shared_state: dict[str, Any],
        tool_history: list[dict[str, Any]],
        research_context: str = "",
        chat_context: str = "",
    ) -> WorkflowCheckpoint:
        """Save a state checkpoint after an agent step."""
        checkpoint = WorkflowCheckpoint(
            workflow_id=workflow_id,
            agent_name=agent_name,
            shared_state=shared_state,
            tool_history=tool_history,
            research_context=research_context,
            chat_context=chat_context,
        )
        self.db.add(checkpoint)
        await self.db.flush()
        logger.info("Saved checkpoint for workflow=%s agent=%s", workflow_id, agent_name)
        return checkpoint

    async def get_latest_checkpoint(self, workflow_id: uuid.UUID) -> WorkflowCheckpoint | None:
        """Get the most recent checkpoint for a workflow."""
        result = await self.db.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_id)
            .order_by(WorkflowCheckpoint.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_checkpoints(self, workflow_id: uuid.UUID) -> list[WorkflowCheckpoint]:
        """Get all checkpoints for a workflow ordered by timestamp."""
        result = await self.db.execute(
            select(WorkflowCheckpoint)
            .where(WorkflowCheckpoint.workflow_id == workflow_id)
            .order_by(WorkflowCheckpoint.created_at.asc())
        )
        return list(result.scalars().all())

    # --- Approvals ---

    async def create_approval(
        self,
        workflow_id: uuid.UUID,
        agent_name: str,
    ) -> WorkflowApproval:
        """Create a pending approval request."""
        approval = WorkflowApproval(
            workflow_id=workflow_id,
            agent_name=agent_name,
            status="pending",
        )
        self.db.add(approval)
        await self.db.flush()
        return approval

    async def get_pending_approval(self, workflow_id: uuid.UUID) -> WorkflowApproval | None:
        """Get current pending approval for a workflow."""
        result = await self.db.execute(
            select(WorkflowApproval)
            .where(
                WorkflowApproval.workflow_id == workflow_id,
                WorkflowApproval.status == "pending",
            )
            .order_by(WorkflowApproval.requested_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_approval(
        self,
        approval_id: uuid.UUID,
        status: str,
        comments: str | None = None,
    ) -> WorkflowApproval | None:
        """Update approval decision."""
        result = await self.db.execute(
            select(WorkflowApproval).where(WorkflowApproval.id == approval_id)
        )
        approval = result.scalar_one_or_none()
        if not approval:
            return None

        approval.status = status
        approval.comments = comments
        approval.decided_at = datetime.utcnow()
        await self.db.flush()
        return approval

    async def get_approvals(self, workflow_id: uuid.UUID) -> list[WorkflowApproval]:
        """Get all approval records for a workflow."""
        result = await self.db.execute(
            select(WorkflowApproval)
            .where(WorkflowApproval.workflow_id == workflow_id)
            .order_by(WorkflowApproval.requested_at.asc())
        )
        return list(result.scalars().all())

    # --- Planning Memory ---

    async def save_planning_memory(
        self,
        goal: str,
        plan: str,
        success_score: float = 100.0,
        execution_time: float = 0.0,
    ) -> PlanningMemory:
        """Save a completed planning memory into DB."""
        memory = PlanningMemory(
            goal=goal,
            plan=plan,
            success_score=success_score,
            execution_time=execution_time,
        )
        self.db.add(memory)
        await self.db.flush()
        return memory

    # --- Schedules ---

    async def create_schedule(
        self,
        title: str,
        user_request: str,
        cron_expression: str = "0 0 * * *",
        require_approval_agents: list[str] | None = None,
    ) -> WorkflowSchedule:
        """Create a scheduled workflow rule."""
        schedule = WorkflowSchedule(
            title=title,
            user_request=user_request,
            cron_expression=cron_expression,
            require_approval_agents=require_approval_agents or [],
            status="active",
        )
        self.db.add(schedule)
        await self.db.flush()
        return schedule

    async def list_schedules(self) -> list[WorkflowSchedule]:
        """List active workflow schedules."""
        result = await self.db.execute(
            select(WorkflowSchedule).order_by(WorkflowSchedule.created_at.desc())
        )
        return list(result.scalars().all())
