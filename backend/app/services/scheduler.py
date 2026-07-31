"""
Background Workflow Scheduler.

Manages scheduled and background autonomous workflow executions.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from app.core.logging import get_logger
from app.db.database import async_session_factory
from app.repositories.workflow_repository import WorkflowRepository

logger = get_logger(__name__)


class WorkflowScheduler:
    """
    Periodic background runner that checks for pending scheduled workflows.
    """

    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the background scheduler loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("WorkflowScheduler started in background")

    def stop(self) -> None:
        """Stop the background scheduler loop."""
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
            logger.info("WorkflowScheduler stopped")

    async def _run_loop(self) -> None:
        """Main loop that runs every 60 seconds to check active schedules."""
        while self._running:
            try:
                await self._check_and_run_schedules()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)

            await asyncio.sleep(60)

    async def _check_and_run_schedules(self) -> None:
        """Check database schedules and spawn workflows when due."""
        async with async_session_factory() as session:
            try:
                repo = WorkflowRepository(session)
                schedules = await repo.list_schedules()
                now = datetime.utcnow()

                for sched in schedules:
                    if sched.status != "active":
                        continue

                    # If next_run_at is reached or last_run_at is None
                    if sched.next_run_at is None or sched.next_run_at <= now:
                        logger.info("Scheduler triggering workflow for schedule: %s", sched.title)
                        
                        # Create workflow instance
                        import uuid
                        wf = await repo.create_workflow(
                            session_id=uuid.uuid4(),
                            user_request=sched.user_request,
                            title=f"[Scheduled] {sched.title}",
                            require_approval_agents=sched.require_approval_agents,
                        )
                        sched.last_run_at = now
                        # Simple default 24h next run calculation
                        sched.next_run_at = now + timedelta(days=1)
                        await session.commit()
            except Exception as e:
                logger.error("Failed checking scheduled workflows: %s", e)


# Global scheduler instance
_scheduler_instance: WorkflowScheduler | None = None


def get_workflow_scheduler() -> WorkflowScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = WorkflowScheduler()
    return _scheduler_instance
