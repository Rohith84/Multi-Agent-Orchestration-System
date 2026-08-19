import json
import uuid
import pytest
from pathlib import Path

from app.db.database import async_session_factory, init_db
from app.orchestration.workflow import WorkflowExecutor
from app.repositories.workflow_repository import WorkflowRepository


@pytest.mark.asyncio
async def test_phase1_workflow_execution():
    """
    Integration test for Phase 1 core workflow reliability:
    1. Approval pause gate behavior
    2. Resuming execution from checkpoint
    3. Workspace directory creation and isolation
    """
    # Ensure database schema is initialized
    await init_db()

    async with async_session_factory() as session:
        executor = WorkflowExecutor(session)
        wf_repo = WorkflowRepository(session)
        session_id = uuid.uuid4()

        # Step 1: Execute workflow with approval requirement at 'coder'
        stream = executor.execute(
            user_request="Write a python function to add two numbers",
            session_id=session_id,
            require_approval_agents=["coder"],
        )

        events = []
        async for event in stream:
            events.append(event)
            if "workflow_paused_approval" in event:
                break

        # Assert that the workflow paused at the approval gate
        assert any("workflow_paused_approval" in e for e in events), (
            "Workflow stream did not pause for approval as expected"
        )

        # Parse workflow ID from initial SSE event
        first_event_json = events[0].replace("data: ", "").strip()
        event_data = json.loads(first_event_json)
        workflow_id = uuid.UUID(event_data["workflow_id"])

        # Assert workflow status in DB is paused_approval
        wf = await wf_repo.get_workflow(workflow_id)
        assert wf is not None
        assert wf.status == "paused_approval"

        # Step 2: Resume execution from stored checkpoint starting at 'tester'
        resume_stream = executor.execute(
            user_request="Write a python function to add two numbers",
            session_id=session_id,
            workflow_id=workflow_id,
            resume_agent="tester",
        )

        resume_events = [e async for e in resume_stream]
        assert any("workflow_complete" in e for e in resume_events), (
            "Resumed workflow failed to complete cleanly"
        )

        # Step 3: Verify workspace sandbox directory isolation
        workspace_dir = Path("sandbox_workspace") / str(session_id)
        assert workspace_dir.exists(), f"Workspace directory {workspace_dir} was not created"
