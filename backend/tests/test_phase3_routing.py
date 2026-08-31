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
    """Verify that a simple informational question skips research, coder, and tester nodes."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    # Mock Planner to require only reviewer for simple Q&A
    mock_plan = "This is a simple informational answer.\nREQUIRED_AGENTS: reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = "Research notes"
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
    """Verify that repair loop retries when quality gate fails, and succeeds when quality gate passes."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    mock_plan = "Plan to write code.\nREQUIRED_AGENTS: research, coder, tester, reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.validator.DeterministicValidator.run_full_quality_gate", new_callable=AsyncMock) as mock_val_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = "Architecture and math library research notes"
        mock_coder_exec.return_value = "def add(a, b): return a + b"
        mock_tester_exec.return_value = {
            "output": "Test generated and coverage analyzed",
            "tester_analysis": "Adequate coverage"
        }
        
        # First execution of Quality Gate fails, second passes
        mock_val_exec.side_effect = [
            {
                "deterministic_checks": {"status": "FAIL", "output": "SyntaxError"},
                "ruff": {"status": "FAIL", "output": "F821"},
                "pytest": {"status": "FAIL", "output": "FAILED"},
                "bandit": {"status": "PASS", "output": "clean"},
                "quality_gate": "FAIL",
                "test_passed": False,
            },
            {
                "deterministic_checks": {"status": "PASS", "output": "clean"},
                "ruff": {"status": "PASS", "output": "clean"},
                "pytest": {"status": "PASS", "output": "passed"},
                "bandit": {"status": "PASS", "output": "clean"},
                "quality_gate": "PASS",
                "test_passed": True,
            }
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
            mock_res_exec.assert_called_once()
            
            # Coder runs first attempt, then runs again on repair retry
            assert mock_coder_exec.call_count == 2
            # Tester runs first time, then second time on repair
            assert mock_tester_exec.call_count == 2
            assert mock_val_exec.call_count == 2
            mock_rev_exec.assert_called_once()
            
            assert any("repair_loop_retry" in e for e in events)
            assert any("workflow_complete" in e for e in events)


@pytest.mark.asyncio(loop_scope="module")
async def test_dynamic_routing_max_repair_attempts():
    """Verify that repair loop aborts and forwards to reviewer after 3 failed attempts."""
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    
    mock_plan = "Plan to write buggy code.\nREQUIRED_AGENTS: research, coder, tester, reviewer"
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.validator.DeterministicValidator.run_full_quality_gate", new_callable=AsyncMock) as mock_val_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = "Research notes for buggy code"
        mock_coder_exec.return_value = "def buggy(): raise ValueError()"
        mock_tester_exec.return_value = {
            "output": "Test generated",
            "tester_analysis": "Coverage insufficient"
        }
        
        # Quality Gate always fails
        mock_val_exec.return_value = {
            "deterministic_checks": {"status": "FAIL", "output": "SyntaxError"},
            "ruff": {"status": "FAIL", "output": "F821"},
            "pytest": {"status": "FAIL", "output": "FAILED"},
            "bandit": {"status": "PASS", "output": "clean"},
            "quality_gate": "FAIL",
            "test_passed": False,
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
            
            mock_res_exec.assert_called_once()
            assert mock_coder_exec.call_count == 3
            assert mock_tester_exec.call_count == 3
            assert mock_val_exec.call_count == 3
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
         patch("app.agents.validator.DeterministicValidator.run_full_quality_gate", new_callable=AsyncMock) as mock_val_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = "Notes"
        mock_coder_exec.return_value = "Code"
        mock_tester_exec.return_value = {
            "output": "Pass",
            "tester_analysis": "Adequate"
        }
        mock_val_exec.return_value = {
            "deterministic_checks": {"status": "PASS", "output": "clean"},
            "ruff": {"status": "PASS", "output": "clean"},
            "pytest": {"status": "PASS", "output": "passed"},
            "bandit": {"status": "PASS", "output": "clean"},
            "quality_gate": "PASS",
            "test_passed": True,
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
            
            # Fallback executes all 5 agents: Planner -> Research -> Coder -> Tester -> Reviewer
            mock_plan_exec.assert_called_once()
            mock_res_exec.assert_called_once()
            mock_coder_exec.assert_called_once()
            mock_tester_exec.assert_called_once()
            mock_val_exec.assert_called_once()
            mock_rev_exec.assert_called_once()
            
            assert any("workflow_complete" in e for e in events)


@pytest.mark.asyncio(loop_scope="module")
async def test_app_build_task_dispatches_research_and_passes_notes_to_coder():
    """
    Validation Test: Task 'Build a simple task management application with a dashboard...'
    Verifies:
      1. Planner -> Research -> Coder -> Tester -> Reviewer timeline order
      2. Research Agent is executed and NOT silently skipped even if Planner's LLM omitted 'research'
      3. Research output ('research_notes') is explicitly passed to Coder Agent
    """
    await engine.dispose()
    await init_db()
    
    session_id = uuid.uuid4()
    user_req = "Build a simple task management application with a dashboard, task creation, task status tracking, priority levels, and a clean responsive UI."
    
    # Intentionally omit 'research' from REQUIRED_AGENTS line to test orchestration override
    mock_plan = (
        "Task Summary: Build task management app\n"
        "File Manifest:\n"
        "  - app/main.py\n"
        "REQUIRED_AGENTS: coder, tester, reviewer"
    )
    
    expected_research_output = (
        "==================================================\n"
        "RESEARCH SUMMARY\n"
        "==================================================\n"
        "FastAPI + React Dashboard Architecture & State Patterns."
    )
    
    with patch("app.agents.planner.PlannerAgent.execute", new_callable=AsyncMock) as mock_plan_exec, \
         patch("app.agents.research.ResearchAgent.execute", new_callable=AsyncMock) as mock_res_exec, \
         patch("app.agents.coder.CoderAgent.execute", new_callable=AsyncMock) as mock_coder_exec, \
         patch("app.agents.tester.TesterAgent.execute", new_callable=AsyncMock) as mock_tester_exec, \
         patch("app.agents.validator.DeterministicValidator.run_full_quality_gate", new_callable=AsyncMock) as mock_val_exec, \
         patch("app.agents.reviewer.ReviewerAgent.execute", new_callable=AsyncMock) as mock_rev_exec:
         
        mock_plan_exec.return_value = mock_plan
        mock_res_exec.return_value = expected_research_output
        mock_coder_exec.return_value = "```python file=\"main.py\"\n# code\n```"
        mock_tester_exec.return_value = {
            "output": "All tests generated",
            "tester_analysis": "Adequate coverage"
        }
        mock_val_exec.return_value = {
            "deterministic_checks": {"status": "PASS", "output": "clean"},
            "ruff": {"status": "PASS", "output": "clean"},
            "pytest": {"status": "PASS", "output": "passed"},
            "bandit": {"status": "PASS", "output": "clean"},
            "quality_gate": "PASS",
            "test_passed": True,
        }
        mock_rev_exec.return_value = {
            "output": "Excellent architecture",
            "quality_gate": "PASS",
            "overall_score": 95.0
        }
        
        async with async_session_factory() as session:
            executor = WorkflowExecutor(session)
            stream = executor.execute(user_request=user_req, session_id=session_id)
            
            events = [e async for e in stream]
            
            # 1. Verify Research executed (was NOT silently skipped)
            mock_res_exec.assert_called_once()
            
            # 2. Verify Coder received the exact research_notes from Research Agent
            mock_coder_exec.assert_called_once()
            coder_call_args = mock_coder_exec.call_args
            assert coder_call_args is not None
            passed_research_notes = coder_call_args.kwargs.get("research_notes")
            assert passed_research_notes == expected_research_output, (
                f"Coder did not receive Research notes! Received: {passed_research_notes}"
            )
            
            # 3. Verify sequence of events in SSE stream
            agent_starts = [
                json.loads(e.replace("data: ", ""))["agent"]
                for e in events
                if "agent_start" in e
            ]
            assert agent_starts == ["planner", "research", "coder", "tester", "reviewer"], (
                f"Timeline sequence mismatch! Expected ['planner', 'research', 'coder', 'tester', 'reviewer'], got {agent_starts}"
            )
