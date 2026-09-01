"""
Unit and Integration Tests for Phase 10: Dynamic Graph Integration.

Validates:
1. Integration of PlanContract, CodeContract, Quality Gate, and Reviewer into DynamicGraphCompiler execution path.
2. WorkspaceService(db=None) isolated execution behavior.
3. Arbitrary node ID resolution using graph topology.
4. Coding workflow bypass protection (rejection and contract enforcement).
5. Non-coding workflows execution.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.planner import PlannerResult
from app.ai.ollama_client import OllamaClient
from app.orchestration.dynamic_graph import DynamicGraphCompiler
from app.orchestration.graph_validator import GraphContractValidationError
from app.schemas.contracts import AgentType, PlanContract, PlanSubtask
from app.schemas.tool_result import ToolResult, ToolStatus
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
    # Valid Planner JSON return
    planner_json = json.dumps({
        "task_summary": "CLI Calculator",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research math CLI", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Implement calc", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Write tests", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Review", "dependencies": [3]},
        ],
        "file_manifest": ["calculator.py", "test_calculator.py"],
        "acceptance_criteria": ["All tests pass"]
    })

    coder_response = '```python filepath="calculator.py"\ndef add(a: float, b: float) -> float:\n    return a + b\n```\nImplementation summary complete.'
    tester_response = '```python filepath="test_calculator.py"\nfrom calculator import add\n\ndef test_add():\n    assert add(2, 3) == 5\n```\nCoverage assessment: ADEQUATE.'
    reviewer_response = "### Review Summary\nClean implementation.\n\n### Quality Score\n90/100\n\n### Final Status\nAPPROVED\n"

    async def mock_chat(messages, model=None, max_tokens=None):
        content = messages[0].get("content", "")
        if "Planner Agent" in content:
            return planner_json
        elif "Coding Agent" in content:
            return coder_response
        elif "Testing Agent" in content:
            return tester_response
        elif "Reviewer Agent" in content:
            return reviewer_response
        return "Generic LLM output"

    client.chat = AsyncMock(side_effect=mock_chat)
    return client


# ============================================================================
# 1 & 20-21. VALID CODING WORKFLOW REACHES QUALITY GATE AND REVIEWER
# ============================================================================
@pytest.mark.asyncio
async def test_1_20_21_valid_coding_workflow(mock_ollama_client, tmp_path: Path):
    """1, 20, 21. Valid calculator coding workflow reaches Quality Gate and Reviewer."""
    ws = WorkspaceService(db=None, session_id="test_sess_1", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
            {"id": "c1", "type": "coder"},
            {"id": "t1", "type": "tester"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [
            {"source": "p1", "target": "r1"},
            {"source": "r1", "target": "c1"},
            {"source": "c1", "target": "t1"},
            {"source": "t1", "target": "rev1"},
        ],
    }

    compiled = compiler.compile(graph_json)

    # Mock tool results for Quality Gate
    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="1 passed", stderr="", duration_ms=20.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Create CLI calculator", "session_id": "test_sess_1"})

    assert final_state["quality_gate"] == "PASS"
    assert final_state["validated_plan"] is not None
    assert (tmp_path / "calculator.py").exists()
    assert (tmp_path / "test_calculator.py").exists()
    assert "APPROVED" in final_state["node_outputs"]["rev1"]


# ============================================================================
# 2 & 3. PLANNER CONTRACT FAILURE STOPS WORKFLOW (577 STEPS)
# ============================================================================
@pytest.mark.asyncio
async def test_2_3_planner_contract_failure_stops_workflow(mock_ollama_client, tmp_path: Path):
    """2-3. Planner contract failure (e.g. 577 tasks) stops workflow with 0 downstream execution."""
    ws = WorkspaceService(db=None, session_id="test_sess_2", workspace_dir=tmp_path)

    # Mock Planner to return 577 steps
    runaway_planner_json = json.dumps({
        "task_summary": "Runaway",
        "subtasks": [{"id": i, "agent": "coder", "description": f"d{i}", "dependencies": []} for i in range(1, 578)]
    })
    mock_ollama_client.chat = AsyncMock(return_value=runaway_planner_json)

    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)
    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "c1", "type": "coder"},
            {"id": "t1", "type": "tester"},
        ],
        "edges": [{"source": "p1", "target": "c1"}, {"source": "c1", "target": "t1"}],
    }

    compiled = compiler.compile(graph_json)
    final_state = await compiled.ainvoke({"user_request": "Runaway plan request", "session_id": "test_sess_2"})

    assert final_state["quality_gate"] in ("FAIL", "BLOCKED")
    assert len(final_state["errors"]) > 0
    assert "PlanContract rejected" in str(final_state["errors"][0])
    assert final_state["node_outputs"]["c1"] == "Skipped — PlanContract validation failed"
    assert final_state["node_outputs"]["t1"] == "Skipped — Contract boundary validation failed"
    assert not (tmp_path / "calculator.py").exists()


# ============================================================================
# 4. INVALID GRAPH REJECTED BEFORE COMPILATION
# ============================================================================
def test_4_invalid_graph_rejected_before_compilation():
    """4. Invalid graph (self-loop / duplicate nodes) rejected before compilation."""
    compiler = DynamicGraphCompiler()
    invalid_graph = {
        "nodes": [{"id": "n1", "type": "coder"}],
        "edges": [{"source": "n1", "target": "n1"}],
    }
    with pytest.raises(GraphContractValidationError):
        compiler.compile(invalid_graph)


# ============================================================================
# 5, 6, 10, 11. SHARED WORKSPACE & TESTER PERSISTENCE (NO PYTEST IN TESTER)
# ============================================================================
@pytest.mark.asyncio
async def test_5_6_10_11_shared_workspace_and_tester_behavior(mock_ollama_client, tmp_path: Path):
    """5, 6, 10, 11. Coder and Tester write to shared WorkspaceService; Tester does NOT execute pytest."""
    ws = WorkspaceService(db=None, session_id="test_sess_3", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "c1", "type": "coder"},
            {"id": "t1", "type": "tester"},
        ],
        "edges": [{"source": "p1", "target": "c1"}, {"source": "c1", "target": "t1"}],
    }
    compiled = compiler.compile(graph_json)

    with patch("app.agents.validator.DeterministicValidator._run_pytest") as mock_pytest_run:
        final_state = await compiled.ainvoke({"user_request": "Build math CLI", "session_id": "test_sess_3"})
        mock_pytest_run.assert_not_called()  # Tester does NOT execute pytest

    assert (tmp_path / "calculator.py").exists()
    assert (tmp_path / "test_calculator.py").exists()


# ============================================================================
# 7, 8, 9. CODECONTRACT EXECUTES AFTER CODER & BLOCKS DOWNSTREAM
# ============================================================================
@pytest.mark.asyncio
async def test_7_8_9_code_contract_failure_blocks_tester_and_quality_gate(mock_ollama_client, tmp_path: Path):
    """7-9. CodeContract failure after Coder blocks Tester and Quality Gate execution."""
    ws = WorkspaceService(db=None, session_id="test_sess_4", workspace_dir=tmp_path)

    # Coder outputs placeholder '# TODO: implement'
    placeholder_coder = '```python filepath="calculator.py"\n# TODO: implement\npass\n```'
    async def mock_chat_placeholder(messages, model=None, max_tokens=None):
        content = messages[0].get("content", "")
        if "Planner Agent" in content:
            return json.dumps({"task_summary": "p", "task_type": "coding", "complexity": "low", "required_agents": ["coder"], "subtasks": [{"id": 1, "agent": "research", "description": "d1", "dependencies": []}, {"id": 2, "agent": "coder", "description": "d2", "dependencies": [1]}, {"id": 3, "agent": "tester", "description": "d3", "dependencies": [2]}], "file_manifest": ["calculator.py"]})
        return placeholder_coder

    mock_ollama_client.chat = AsyncMock(side_effect=mock_chat_placeholder)

    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)
    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "c1", "type": "coder"},
            {"id": "t1", "type": "tester"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [
            {"source": "p1", "target": "c1"},
            {"source": "c1", "target": "t1"},
            {"source": "t1", "target": "rev1"},
        ],
    }

    compiled = compiler.compile(graph_json)
    final_state = await compiled.ainvoke({"user_request": "Build placeholder", "session_id": "test_sess_4"})

    assert final_state["quality_gate"] in ("FAIL", "CONTRACT_FAILURE")
    assert "CodeContract Violation" in str(final_state["errors"][0])
    assert final_state["node_outputs"]["t1"] == "Skipped — Contract boundary validation failed"
    assert "REJECTED" in final_state["node_outputs"]["rev1"] or "CONTRACT_FAILURE" in final_state["node_outputs"]["rev1"]


# ============================================================================
# 12, 13, 14, 15, 16. REVIEWER RECEIVES AUTHORITATIVE QUALITY GATE EVIDENCE
# ============================================================================
@pytest.mark.asyncio
async def test_12_to_16_reviewer_receives_authoritative_evidence(mock_ollama_client, tmp_path: Path):
    """12-16. Reviewer receives actual validation_results, ToolResult, CodeContract evidence; cannot override state."""
    ws = WorkspaceService(db=None, session_id="test_sess_5", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "c1", "type": "coder"},
            {"id": "t1", "type": "tester"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [
            {"source": "p1", "target": "c1"},
            {"source": "c1", "target": "t1"},
            {"source": "t1", "target": "rev1"},
        ],
    }

    compiled = compiler.compile(graph_json)

    # Pytest failed in Quality Gate
    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=1, stdout="AssertionError: 2 != 3", stderr="", duration_ms=20.0, status=ToolStatus.TEST_FAILURE)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Failing test request", "session_id": "test_sess_5"})

    assert final_state["quality_gate"] in ("FAIL", "TEST_FAILURE")
    assert "REJECTED" in final_state["node_outputs"]["rev1"]


# ============================================================================
# 17, 18, 19. INFRASTRUCTURE ERROR & RAG EVIDENCE TRANSMISSION
# ============================================================================
@pytest.mark.asyncio
async def test_17_18_19_infrastructure_and_rag_errors(mock_ollama_client, tmp_path: Path):
    """17-19. Ruff/Pytest/RAG infrastructure errors reach Reviewer accurately as INFRASTRUCTURE_ERROR."""
    ws = WorkspaceService(db=None, session_id="test_sess_6", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "c1", "type": "coder"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [{"source": "p1", "target": "c1"}, {"source": "c1", "target": "rev1"}],
    }

    compiled = compiler.compile(graph_json)

    # Ruff infrastructure failure
    mock_ruff_infra = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=None, stdout="", stderr="", execution_error="FileNotFoundError: ruff missing", duration_ms=1.0, status=ToolStatus.INFRASTRUCTURE_ERROR)
    mock_pytest_pass = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit_pass = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff_infra, mock_bandit_pass]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest_pass):

        final_state = await compiled.ainvoke({"user_request": "Infra fail request", "session_id": "test_sess_6"})

    assert final_state["quality_gate"] in ("FAIL", "INFRASTRUCTURE_FAILURE")
    assert "INFRASTRUCTURE_ERROR" in final_state["node_outputs"]["rev1"]


# ============================================================================
# 22 & 23. CODING WORKFLOW BYPASS PROTECTION (REJECTION & CONTRACT ENFORCEMENT)
# ============================================================================
@pytest.mark.asyncio
async def test_22_23_coding_workflow_bypass_protection(mock_ollama_client):
    """22-23. Coding workflow graph missing 'planner' is REJECTED at compilation."""
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client)

    # Bypass Graph: Coder -> Reviewer without Planner
    bypass_graph = {
        "nodes": [
            {"id": "c1", "type": "coder"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [{"source": "c1", "target": "rev1"}],
    }

    # Must be explicitly REJECTED at compilation
    with pytest.raises(GraphContractValidationError) as exc_info:
        compiler.compile(bypass_graph)

    assert "MUST include a 'planner' node" in str(exc_info.value)


# ============================================================================
# 24. NON-CODING WORKFLOW (PURE RESEARCH)
# ============================================================================
@pytest.mark.asyncio
async def test_24_non_coding_workflow(mock_ollama_client):
    """24. Custom non-coding workflow (Planner -> Research -> Reviewer) executes cleanly without CodeContract requirement."""
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [{"source": "p1", "target": "r1"}, {"source": "r1", "target": "rev1"}],
    }

    compiled = compiler.compile(graph_json)
    final_state = await compiled.ainvoke({"user_request": "Research Python 3.13 features"})

    assert "p1" in final_state["node_outputs"]
    assert "r1" in final_state["node_outputs"]
    assert "rev1" in final_state["node_outputs"]


# ============================================================================
# 25. ARBITRARY NODE IDS & TOPOLOGY RESOLUTION
# ============================================================================
@pytest.mark.asyncio
async def test_25_arbitrary_node_ids_and_topology_resolution(mock_ollama_client, tmp_path: Path):
    """25. Arbitrary node IDs (my_planner, my_coder, my_reviewer) resolved deterministically using graph topology."""
    ws = WorkspaceService(db=None, session_id="test_sess_7", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "custom_planner_101", "type": "planner"},
            {"id": "custom_coder_202", "type": "coder"},
            {"id": "custom_reviewer_303", "type": "reviewer"},
        ],
        "edges": [
            {"source": "custom_planner_101", "target": "custom_coder_202"},
            {"source": "custom_coder_202", "target": "custom_reviewer_303"},
        ],
    }

    compiled = compiler.compile(graph_json)

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Custom node ID task", "session_id": "test_sess_7"})

    assert "custom_planner_101" in final_state["node_outputs"]
    assert "custom_coder_202" in final_state["node_outputs"]
    assert "custom_reviewer_303" in final_state["node_outputs"]
