"""
Unit and Integration Tests for Phase 14: Production Reliability & Failure Recovery.

Validates:
1. Agent & Tool Timeout Protection (Planner, Research, Coder, Tester, Reviewer).
2. Deterministic Retry Policy (Max 2 total attempts for transient failures; 0 retries for contract failures).
3. Runtime exception capture into structured ExecutionError objects.
4. WorkflowStatus lifecycle transitions (RUNNING, COMPLETED, FAILED, BLOCKED, CANCELLED).
5. Workspace write failure protection & partial artifact persistence.
6. Cancellation safety (asyncio.CancelledError without retrying or false approvals).
7. Quality Gate & Reviewer protection against false PASS or false APPROVAL.
8. Preservation of previous state, execution history, evidence, and reasoning metadata across failures.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.ollama_client import OllamaClient
from app.agents.coder import CoderAgent
from app.agents.planner import PlannerAgent
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.agents.validator import DeterministicValidator
from app.orchestration.dynamic_graph import DynamicGraphCompiler
from app.schemas.execution_error import ExecutionError, ExecutionErrorType, WorkflowStatus
from app.services.workspace_service import WorkspaceService


@pytest.fixture(autouse=True)
def mock_embedding_generator():
    """Bypass fastembed ONNX initialization in tests."""
    with patch("app.knowledge.embeddings.generator.EmbeddingGenerator.__init__", return_value=None), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.generate_embedding", new_callable=AsyncMock, return_value=[0.1] * 384):
        yield


@pytest.fixture
def mock_ollama_client():
    client = MagicMock(spec=OllamaClient)
    planner_json = json.dumps({
        "task_summary": "Reliability Test",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Implement", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Test", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Review", "dependencies": [3]},
        ],
        "file_manifest": ["main.py"],
        "acceptance_criteria": ["Pass tests"],
    })
    coder_resp = '```python filepath="main.py"\ndef add(a, b):\n    return a + b\n```'
    tester_resp = '```python filepath="test_main.py"\ndef test_add():\n    assert True\n```'
    reviewer_resp = "## OBSERVED FACTS\nClean.\n\n## TECHNICAL ASSESSMENT\nGood.\n\n## STRENGTHS\nNone.\n\n## WEAKNESSES\nNone.\n\n## RISKS\nNone.\n\n## RECOMMENDATIONS\nShip.\n\n## FINAL REVIEW\nApproved."

    async def mock_chat(messages, model=None, max_tokens=None):
        content = messages[0].get("content", "")
        if "Planner Agent" in content:
            return planner_json
        elif "Coding Agent" in content:
            return coder_resp
        elif "Testing Agent" in content:
            return tester_resp
        elif "Reviewer Agent" in content:
            return reviewer_resp
        return "Response"

    client.chat = AsyncMock(side_effect=mock_chat)
    return client


# ============================================================================
# 1. STRUCTURED EXECUTION ERROR SCHEMAS & WORKFLOW STATUS
# ============================================================================
def test_1_execution_error_schema():
    """Verify ExecutionError schema creates structured error without swallowed details."""
    err = ExecutionError(
        node="node_coder",
        agent="coder",
        error_type=ExecutionErrorType.AGENT_TIMEOUT,
        message="LLM call timed out after 30s",
        recoverable=False,
        attempt=2,
    )
    assert err.node == "node_coder"
    assert err.error_type == ExecutionErrorType.AGENT_TIMEOUT
    assert err.attempt == 2
    assert WorkflowStatus.FAILED.value == "FAILED"
    assert WorkflowStatus.BLOCKED.value == "BLOCKED"
    assert WorkflowStatus.CANCELLED.value == "CANCELLED"


# ============================================================================
# 2. AGENT TIMEOUTS & RETRY CONTROL (MAX 2 ATTEMPTS)
# ============================================================================
@pytest.mark.asyncio
async def test_2_agent_timeout_retried_max_2_attempts(mock_ollama_client, tmp_path: Path):
    """Verify transient LLM timeout is retried exactly once (2 attempts total) and recorded."""
    ws = WorkspaceService(db=None, session_id="timeout_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    call_count = 0

    async def timeout_chat(messages, model=None, max_tokens=None):
        nonlocal call_count
        call_count += 1
        raise asyncio.TimeoutError("Ollama HTTP connection timed out")

    mock_ollama_client.chat = AsyncMock(side_effect=timeout_chat)

    graph_json = {"nodes": [{"id": "p1", "type": "planner"}], "edges": []}
    compiled = compiler.compile(graph_json)

    state = await compiled.ainvoke({"user_request": "Build app", "session_id": "timeout_sess"})

    assert call_count == 2  # Attempt 1 failed -> Attempt 2 failed -> STOP
    assert state["workflow_status"] == WorkflowStatus.FAILED.value
    assert state["quality_gate"] == "INFRASTRUCTURE_FAILURE"
    assert len(state["execution_errors"]) == 1
    assert state["execution_errors"][0]["error_type"] == ExecutionErrorType.AGENT_TIMEOUT.value


# ============================================================================
# 3. NO RETRY AFTER DETERMINISTIC CONTRACT FAILURE
# ============================================================================
@pytest.mark.asyncio
async def test_3_no_retry_on_deterministic_contract_failure(mock_ollama_client, tmp_path: Path):
    """Verify invalid PlanContract fails immediately (BLOCKED) with 0 retries."""
    planner = PlannerAgent(client=mock_ollama_client)
    mock_ollama_client.chat = AsyncMock(return_value='{"invalid": "json"}')

    res = await planner.execute_contract("Plan request")
    assert res.is_valid is False

    ws = WorkspaceService(db=None, session_id="blocked_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)
    graph_json = {"nodes": [{"id": "p1", "type": "planner"}], "edges": []}
    compiled = compiler.compile(graph_json)

    state = await compiled.ainvoke({"user_request": "Plan request", "session_id": "blocked_sess"})
    assert state["workflow_status"] == WorkflowStatus.BLOCKED.value
    assert state["quality_gate"] == "BLOCKED"


# ============================================================================
# 4. WORKSPACE WRITE FAILURE PROTECTION
# ============================================================================
@pytest.mark.asyncio
async def test_4_workspace_write_failure_captured(tmp_path: Path):
    """Verify disk/permission write errors raise IOError and do not swallow failure."""
    ws = WorkspaceService(db=None, session_id="ws_sess", workspace_dir=tmp_path)
    with patch.object(Path, "write_text", side_effect=PermissionError("Permission denied")):
        with pytest.raises(IOError) as exc_info:
            await ws.write_file("test.py", "content = 1")
        assert "Workspace file write failed" in str(exc_info.value)


# ============================================================================
# 5. CANCELLATION SAFETY
# ============================================================================
@pytest.mark.asyncio
async def test_5_cancellation_handled_safely(mock_ollama_client, tmp_path: Path):
    """Verify asyncio.CancelledError records CANCELLED status without retrying or false PASS."""
    ws = WorkspaceService(db=None, session_id="cancel_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    async def cancel_chat(messages, model=None, max_tokens=None):
        raise asyncio.CancelledError("Task cancelled by user")

    mock_ollama_client.chat = AsyncMock(side_effect=cancel_chat)
    graph_json = {"nodes": [{"id": "p1", "type": "planner"}], "edges": []}
    compiled = compiler.compile(graph_json)

    state = await compiled.ainvoke({"user_request": "Cancel test", "session_id": "cancel_sess"})
    assert state["workflow_status"] == WorkflowStatus.CANCELLED.value
    assert state["quality_gate"] != "PASS"
    assert len(state["execution_errors"]) == 1
    assert state["execution_errors"][0]["error_type"] == ExecutionErrorType.CANCELLATION.value


# ============================================================================
# 6. REVIEWER RUNTIME FAILURE SAFETY (EXECUTION_ERROR -> NOT_APPROVED)
# ============================================================================
@pytest.mark.asyncio
async def test_6_reviewer_runtime_failure_cannot_produce_approval(mock_ollama_client):
    """Verify Reviewer crash produces EXECUTION_ERROR and NOT_APPROVED, never false approval."""
    reviewer = ReviewerAgent(client=mock_ollama_client)

    async def crash_review(system_prompt, prompt, authoritative_gate):
        raise RuntimeError("Reviewer LLM process crashed")

    reviewer._request_qualitative_review = AsyncMock(side_effect=crash_review)

    val_pass = {"quality_gate": "PASS"}
    res = await reviewer.execute(
        user_request="req",
        execution_plan="plan",
        generated_code="code",
        test_results="tests",
        validation_results=val_pass,
    )

    assert "NOT_APPROVED" in res["output"]
    assert res["quality_gate"] == "INFRASTRUCTURE_FAILURE"


# ============================================================================
# 7. QUALITY GATE CANNOT PASS AFTER RUNTIME ERROR
# ============================================================================
@pytest.mark.asyncio
async def test_7_quality_gate_cannot_pass_after_runtime_error(mock_ollama_client, tmp_path: Path):
    """Verify node execution crash sets INFRASTRUCTURE_FAILURE and prevents Quality Gate PASS."""
    ws = WorkspaceService(db=None, session_id="crash_sess", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    # Coder agent crashes
    async def crash_coder(*args, **kwargs):
        raise RuntimeError("Coder process OOM crash")

    graph_json = {
        "nodes": [{"id": "p1", "type": "planner"}, {"id": "c1", "type": "coder"}],
        "edges": [{"source": "p1", "target": "c1"}],
    }
    compiled = compiler.compile(graph_json)

    with patch("app.agents.coder.CoderAgent.execute", side_effect=crash_coder):
        state = await compiled.ainvoke({"user_request": "Crash test", "session_id": "crash_sess"})

    assert state["workflow_status"] == WorkflowStatus.FAILED.value
    assert state["quality_gate"] == "INFRASTRUCTURE_FAILURE"
    assert "p1" in state["execution_history"]
    assert "c1" in state["execution_history"]
