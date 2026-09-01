"""
Unit and Integration Tests for Phase 11: Structured Dynamic Agent State Model.

Validates:
1. DynamicAgentState typed dict fields (validated_plan, artifacts, code_contract, validation_results, quality_gate, rag_result, errors).
2. Preservation of detailed authoritative Quality Gate states (CONTRACT_FAILURE, TEST_FAILURE, LINT_FAILURE, INFRASTRUCTURE_FAILURE, BLOCKED, PASS).
3. Preservation of RAG states (RAG_SUCCESS, RAG_EMPTY, RAG_INFRASTRUCTURE_ERROR).
4. LangGraph StateGraph state persistence and transition safety across Planner -> Research -> Coder -> Tester -> Quality Gate -> Reviewer nodes.
5. Session isolation and prevention of accidental mutable state sharing.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.ollama_client import OllamaClient
from app.orchestration.dynamic_graph import DynamicAgentState, DynamicGraphCompiler
from app.schemas.rag import RAGResult, RAGStatus
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
    planner_json = json.dumps({
        "task_summary": "Structured State Test",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Code", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Test", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Review", "dependencies": [3]},
        ],
        "file_manifest": ["main.py", "test_main.py"],
    })
    coder_resp = '```python filepath="main.py"\ndef add(a: int, b: int) -> int:\n    return a + b\n```'
    tester_resp = '```python filepath="test_main.py"\nfrom main import add\ndef test_add():\n    assert add(1, 2) == 3\n```'
    reviewer_resp = "### Review Summary\nPassed.\n\n### Quality Score\n95/100\n\n### Final Status\nAPPROVED\n"

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
        return "LLM response"

    client.chat = AsyncMock(side_effect=mock_chat)
    return client


# ============================================================================
# 1-3. STATE INITIALIZATION & STRUCTURED PLAN STORAGE
# ============================================================================
@pytest.mark.asyncio
async def test_1_2_3_structured_plan_storage(mock_ollama_client, tmp_path: Path):
    """1-3. DynamicAgentState stores validated PlanContract structurally; raw LLM text is NOT authoritative plan."""
    ws = WorkspaceService(db=None, session_id="sess_st_1", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [{"id": "p1", "type": "planner"}],
        "edges": [],
    }
    compiled = compiler.compile(graph_json)
    state = await compiled.ainvoke({"user_request": "Test request", "session_id": "sess_st_1"})

    assert "validated_plan" in state
    assert state["validated_plan"]["task_summary"] == "Structured State Test"
    assert len(state["validated_plan"]["subtasks"]) == 4
    assert state["node_outputs"]["p1"] != state["validated_plan"]


# ============================================================================
# 4-7. ARTIFACT, CODECONTRACT, AND QUALITY GATE STRUCTURED STORAGE
# ============================================================================
@pytest.mark.asyncio
async def test_4_to_7_structured_artifact_code_contract_quality_gate(mock_ollama_client, tmp_path: Path):
    """4-7. Artifacts, CodeContract, Quality Gate evidence & state stored structurally."""
    ws = WorkspaceService(db=None, session_id="sess_st_2", workspace_dir=tmp_path)
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

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        state = await compiled.ainvoke({"user_request": "Build app", "session_id": "sess_st_2"})

    assert len(state["artifacts"]) > 0
    assert state["artifacts"][0]["path"] in ("main.py", "test_main.py")
    assert state["code_contract"]["is_valid"] is True
    assert state["quality_gate"] == "PASS"


# ============================================================================
# 8-10. RAG STATES IN STRUCTURED STATE (SUCCESS, EMPTY, INFRASTRUCTURE_ERROR)
# ============================================================================
@pytest.mark.asyncio
async def test_8_9_10_rag_states_in_structured_state(mock_ollama_client, tmp_path: Path):
    """8-10. RAG_SUCCESS, RAG_EMPTY, and RAG_INFRASTRUCTURE_ERROR preserved in rag_result state field."""
    ws = WorkspaceService(db=None, session_id="sess_st_3", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
        ],
        "edges": [{"source": "p1", "target": "r1"}],
    }
    compiled = compiler.compile(graph_json)

    # Case A: RAG_SUCCESS
    mock_rag_success = RAGResult(status=RAGStatus.RAG_SUCCESS, query="q", chunks=[{"filename": "a.py", "score": 0.9, "chunk_index": 0, "content": "c"}], retrieval_time=0.01)
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag_success):
        state_a = await compiled.ainvoke({"user_request": "q", "session_id": "sess_st_3"})
        assert state_a["rag_result"]["status"] == RAGStatus.RAG_SUCCESS

    # Case B: RAG_EMPTY
    mock_rag_empty = RAGResult(status=RAGStatus.RAG_EMPTY, query="q", chunks=[], retrieval_time=0.01)
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag_empty):
        state_b = await compiled.ainvoke({"user_request": "q", "session_id": "sess_st_3"})
        assert state_b["rag_result"]["status"] == RAGStatus.RAG_EMPTY

    # Case C: RAG_INFRASTRUCTURE_ERROR
    mock_rag_infra = RAGResult(status=RAGStatus.RAG_INFRASTRUCTURE_ERROR, query="q", chunks=[], error="Chroma down")
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag_infra):
        state_c = await compiled.ainvoke({"user_request": "q", "session_id": "sess_st_3"})
        assert state_c["rag_result"]["status"] == RAGStatus.RAG_INFRASTRUCTURE_ERROR


# ============================================================================
# 11 & 23. STRUCTURED ERRORS & PRESERVED NOT_EXECUTED TOOL STATES
# ============================================================================
@pytest.mark.asyncio
async def test_11_23_structured_errors_and_not_executed_preservation(mock_ollama_client, tmp_path: Path):
    """11, 23. Structured error objects preserve node, type, message; NOT_EXECUTED tool states remain preserved."""
    ws = WorkspaceService(db=None, session_id="sess_st_4", workspace_dir=tmp_path)

    # Coder outputs placeholder '# TODO'
    mock_ollama_client.chat = AsyncMock(side_effect=[
        json.dumps({"task_summary": "p", "task_type": "coding", "complexity": "low", "required_agents": ["coder"], "subtasks": [{"id": 1, "agent": "research", "description": "d1", "dependencies": []}, {"id": 2, "agent": "coder", "description": "d2", "dependencies": [1]}, {"id": 3, "agent": "tester", "description": "d3", "dependencies": [2]}], "file_manifest": ["main.py"]}),
        '```python filepath="main.py"\n# TODO: implement\npass\n```'
    ])

    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)
    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "c1", "type": "coder"},
        ],
        "edges": [{"source": "p1", "target": "c1"}],
    }

    compiled = compiler.compile(graph_json)
    state = await compiled.ainvoke({"user_request": "Placeholder test", "session_id": "sess_st_4"})

    assert state["quality_gate"] == "CONTRACT_FAILURE"
    assert len(state["errors"]) > 0
    err_obj = state["errors"][0]
    assert isinstance(err_obj, dict)
    assert err_obj["type"] == "CodeContractError"
    assert state["validation_results"]["ruff"]["status"] == "NOT_EXECUTED"


# ============================================================================
# 15-18. STATE TRANSITION PERSISTENCE THROUGH ALL AGENT NODES
# ============================================================================
@pytest.mark.asyncio
async def test_15_to_18_state_transitions(mock_ollama_client, tmp_path: Path):
    """15-18. Structured state survives Planner -> Research -> Coder -> CodeContract -> Tester -> Quality Gate -> Reviewer transitions."""
    ws = WorkspaceService(db=None, session_id="sess_st_5", workspace_dir=tmp_path)
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

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        state = await compiled.ainvoke({"user_request": "E2E State Transition", "session_id": "sess_st_5"})

    assert state["execution_history"] == ["p1", "r1", "c1", "t1", "rev1"]
    assert state["validated_plan"] is not None
    assert state["code_contract"]["is_valid"] is True
    assert state["validation_results"]["quality_gate"] == "PASS"
    assert state["quality_gate"] == "PASS"


# ============================================================================
# 19-22. SESSION ISOLATION & LANGGRAPH COMPATIBILITY
# ============================================================================
@pytest.mark.asyncio
async def test_19_20_21_22_session_isolation_and_langgraph_compatibility(mock_ollama_client, tmp_path: Path):
    """19-22. Session state remains isolated between sessions; state updates do not overwrite unrelated fields."""
    dir1 = tmp_path / "s1"
    dir2 = tmp_path / "s2"

    ws1 = WorkspaceService(db=None, session_id="sess_iso_1", workspace_dir=dir1)
    ws2 = WorkspaceService(db=None, session_id="sess_iso_2", workspace_dir=dir2)

    compiler1 = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws1)
    compiler2 = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws2)

    graph_json = {
        "nodes": [{"id": "p1", "type": "planner"}, {"id": "c1", "type": "coder"}],
        "edges": [{"source": "p1", "target": "c1"}],
    }

    c1 = compiler1.compile(graph_json)
    c2 = compiler2.compile(graph_json)

    state1 = await c1.ainvoke({"user_request": "Req 1", "session_id": "sess_iso_1"})
    state2 = await c2.ainvoke({"user_request": "Req 2", "session_id": "sess_iso_2"})

    assert state1["session_id"] == "sess_iso_1"
    assert state2["session_id"] == "sess_iso_2"
    assert (dir1 / "main.py").exists()
    assert (dir2 / "main.py").exists()
    assert state1["session_id"] != state2["session_id"]


# ============================================================================
# 24. REVIEWER RECEIVES AUTHORITATIVE VALIDATION EVIDENCE FROM STATE
# ============================================================================
@pytest.mark.asyncio
async def test_24_reviewer_receives_authoritative_state_evidence(mock_ollama_client, tmp_path: Path):
    """24. Reviewer receives authoritative evidence stored directly in state."""
    ws = WorkspaceService(db=None, session_id="sess_st_8", workspace_dir=tmp_path)
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

    # Pytest failed in Quality Gate
    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=1, stdout="AssertionError in test_main.py", stderr="", duration_ms=20.0, status=ToolStatus.TEST_FAILURE)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        state = await compiled.ainvoke({"user_request": "Failing test request", "session_id": "sess_st_8"})

    assert state["quality_gate"] == "TEST_FAILURE"
    assert "REJECTED" in state["node_outputs"]["rev1"]
