import pytest
import uuid
import json
from unittest.mock import AsyncMock, patch
from app.db.database import init_db, async_session_factory, engine
from app.orchestration.workflow import WorkflowExecutor
from app.orchestration.graph import create_agent_graph
from app.ai.ollama_client import OllamaClient


@pytest.mark.asyncio(loop_scope="module")
async def test_dynamic_routing_simple_task():
    """Verify that a simple task skips research, coder, and tester nodes."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    # Mock Planner to require only reviewer
    mock_plan = "This is a simple informational plan.\nREQUIRED_AGENTS: reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_rev_exec.return_value = {
            "output": "This is a completed review.",
            "quality_gate": "PASS"
        }
        
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            stream = executor.execute(
                user_request="How old is the Earth?",
                session_id=session_id
            )
            
            events = [e async for e in stream]
            
            # Assertions
            mock_plan_exec.assert_called_once()
            mock_res_exec.assert_not_called()
            mock_coder_exec.assert_not_called()
            mock_tester_exec.assert_not_called()
            mock_rev_exec.assert_called_once()
            
            assert any("workflow_complete" in e for e in events)


@pytest.mark.asyncio(loop_scope="module")
async def test_dynamic_routing_research_task():
    """Verify that a research task executes research node but skips coder and tester."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    # Mock Planner to require research and reviewer
    mock_plan = "Plan to research python libraries.\nREQUIRED_AGENTS: research, reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = "Here are the research notes."
        mock_rev_exec.return_value = {
            "output": "Completed review of research notes.",
            "quality_gate": "PASS"
        }
        
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            stream = executor.execute(
                user_request="Research FastAPI best practices",
                session_id=session_id
            )
            
            events = [e async for e in stream]
            
            # Assertions
            mock_plan_exec.assert_called_once()
            mock_res_exec.assert_called_once()
            mock_coder_exec.assert_not_called()
            mock_tester_exec.assert_not_called()
            mock_rev_exec.assert_called_once()
            
            assert any("workflow_complete" in e for e in events)


@pytest.mark.asyncio(loop_scope="module")
async def test_dynamic_routing_repair_loop_success():
    """Verify that repair loop retries when tester fails, and succeeds when tester passes."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    # Mock Planner to require coder, tester, reviewer (skips research)
    mock_plan = "Plan to write code.\nREQUIRED_AGENTS: coder, tester, reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_coder_exec.return_value = "def add(a, b): return a + b"
        
        # First execution of tester fails, second passes
        mock_tester_exec.side_effect = [
            {"passed": False, "output": "Test failed!", "execution_time": 0.5, "bug_report": {"error": "AssertionError"}},
            {"passed": True, "output": "All tests passed!", "execution_time": 0.5, "bug_report": None}
        ]
        
        mock_rev_exec.return_value = {
            "output": "Perfect code review.",
            "quality_gate": "PASS"
        }
        
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            stream = executor.execute(
                user_request="Write a math library",
                session_id=session_id
            )
            
            events = [e async for e in stream]
            
            # Assertions
            mock_plan_exec.assert_called_once()
            mock_res_exec.assert_not_called()
            
            # Coder runs first attempt, then runs again on repair retry
            assert mock_coder_exec.call_count == 2
            # Tester runs first time (fails), then second time (passes)
            assert mock_tester_exec.call_count == 2
            mock_rev_exec.assert_called_once()
            
            assert any("repair_loop_retry" in e for e in events)
            assert any("workflow_complete" in e for e in events)


@pytest.mark.asyncio(loop_scope="module")
async def test_dynamic_routing_max_repair_attempts():
    """Verify that repair loop aborts and forwards to reviewer after 3 failed attempts."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    mock_plan = "Plan to write buggy code.\nREQUIRED_AGENTS: coder, tester, reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_coder_exec.return_value = "def buggy(): raise ValueError()"
        
        # Tester always fails
        mock_tester_exec.return_value = {
            "passed": False,
            "output": "Test failed persistently!",
            "execution_time": 0.5,
            "bug_report": {"error": "ValueError"}
        }
        
        mock_rev_exec.return_value = {
            "output": "Buggy review.",
            "quality_gate": "FAIL"
        }
        
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            stream = executor.execute(
                user_request="Write a buggy script",
                session_id=session_id
            )
            
            events = [e async for e in stream]
            
            # Coder runs 3 attempts:
            # Attempt 1 (initial) + Attempt 2 (retry 1) + Attempt 3 (retry 2)
            # Wait, our retry check is: `repair_attempts < 3`.
            # First tester node run: repair_attempts becomes 1. Loop back.
            # Second coder run. Second tester run: repair_attempts becomes 2. Loop back.
            # Third coder run. Third tester run: repair_attempts becomes 3.
            # Tester checks: `repair_attempts < 3`. 3 is not < 3, so skip loop and go to reviewer!
            assert mock_coder_exec.call_count == 3
            assert mock_tester_exec.call_count == 3
            mock_rev_exec.assert_called_once()
            
            assert any("workflow_complete" in e for e in events)


@pytest.mark.asyncio(loop_scope="module")
async def test_dynamic_routing_invalid_decision_fallback():
    """Verify that invalid planner routing decisions fall back to running all agents."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    # Planner outputs junk or invalid agents
    mock_plan = "REQUIRED_AGENTS: invalid_agent_name, unknown"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = "Notes"
        mock_coder_exec.return_value = "Code"
        mock_tester_exec.return_value = {
            "passed": True,
            "output": "Pass",
            "execution_time": 0.1,
            "bug_report": None
        }
        mock_rev_exec.return_value = {
            "output": "Review",
            "quality_gate": "PASS"
        }
        
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            stream = executor.execute(
                user_request="Fallback check",
                session_id=session_id
            )
            
            events = [e async for e in stream]
            
            # Since required_agents parsed to empty list, it fell back to all agents!
            mock_plan_exec.assert_called_once()
            mock_res_exec.assert_called_once()
            mock_coder_exec.assert_called_once()
            mock_tester_exec.assert_called_once()
            mock_rev_exec.assert_called_once()
            
            assert any("workflow_complete" in e for e in events)
