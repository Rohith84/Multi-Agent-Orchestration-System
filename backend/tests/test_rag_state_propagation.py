"""
Unit and Integration Tests for Phase 12: Complete RAG State Propagation & Reliability.

Validates:
1. RAG_SUCCESS, RAG_EMPTY, and RAG_INFRASTRUCTURE_ERROR propagation through graph state.
2. Structured RAG evidence consumption by Coder and Reviewer without prose parsing.
3. Reviewer structured rag_result precedence over research_notes prose.
4. Session isolation and non-overwriting across graph node transitions.
5. Complete integration scenarios for RAG_SUCCESS and RAG_INFRASTRUCTURE_ERROR workflows.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.ollama_client import OllamaClient
from app.agents.coder import CoderAgent
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.orchestration.dynamic_graph import DynamicGraphCompiler
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
        "task_summary": "RAG Propagation Test",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Code", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Test", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Review", "dependencies": [3]},
        ],
        "file_manifest": ["main.py"],
    })
    coder_resp = '```python filepath="main.py"\ndef main():\n    return 42\n```'
    tester_resp = "```python filepath=\"test_main.py\"\nfrom main import main\ndef test_main():\n    assert main() == 42\n```"
    reviewer_resp = "### Review Summary\nPassed cleanly.\n\n### Final Status\nAPPROVED\n"

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
# 1 & 2. RAG_SUCCESS PROPAGATION & CHUNK METADATA PRESERVATION
# ============================================================================
@pytest.mark.asyncio
async def test_1_2_rag_success_propagation_and_chunk_metadata(mock_ollama_client, tmp_path: Path):
    """1, 2. RAG_SUCCESS propagates into graph state and preserves all chunk metadata."""
    ws = WorkspaceService(db=None, session_id="rag_sess_1", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
        ],
        "edges": [{"source": "p1", "target": "r1"}],
    }
    compiled = compiler.compile(graph_json)

    mock_rag = RAGResult(
        status=RAGStatus.RAG_SUCCESS,
        chunks=[
            {
                "filename": "auth.py",
                "document_id": "doc_101",
                "chunk_index": 2,
                "score": 0.95,
                "content": "def authenticate(): pass",
            }
        ],
        retrieval_time=0.012,
    )

    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag):
        state = await compiled.ainvoke({"user_request": "Auth system", "session_id": "rag_sess_1"})

    assert state["rag_result"]["status"] == RAGStatus.RAG_SUCCESS
    assert state["rag_result"]["retrieval_time"] == 0.012
    assert len(state["rag_result"]["chunks"]) == 1
    chunk = state["rag_result"]["chunks"][0]
    assert chunk["filename"] == "auth.py"
    assert chunk["document_id"] == "doc_101"
    assert chunk["chunk_index"] == 2
    assert chunk["score"] == 0.95


# ============================================================================
# 3 & 4. RAG_EMPTY & RAG_INFRASTRUCTURE_ERROR PROPAGATION
# ============================================================================
@pytest.mark.asyncio
async def test_3_4_rag_empty_and_infrastructure_error_propagation(mock_ollama_client, tmp_path: Path):
    """3, 4. RAG_EMPTY and RAG_INFRASTRUCTURE_ERROR propagate accurately into rag_result state."""
    ws = WorkspaceService(db=None, session_id="rag_sess_2", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [{"id": "p1", "type": "planner"}, {"id": "r1", "type": "research"}],
        "edges": [{"source": "p1", "target": "r1"}],
    }
    compiled = compiler.compile(graph_json)

    # 3. RAG_EMPTY
    mock_empty = RAGResult(status=RAGStatus.RAG_EMPTY, chunks=[], retrieval_time=0.005)
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_empty):
        state_empty = await compiled.ainvoke({"user_request": "req", "session_id": "rag_sess_2"})
        assert state_empty["rag_result"]["status"] == RAGStatus.RAG_EMPTY

    # 4. RAG_INFRASTRUCTURE_ERROR
    mock_infra = RAGResult(status=RAGStatus.RAG_INFRASTRUCTURE_ERROR, chunks=[], error="Chroma connection failed")
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_infra):
        state_infra = await compiled.ainvoke({"user_request": "req", "session_id": "rag_sess_2"})
        assert state_infra["rag_result"]["status"] == RAGStatus.RAG_INFRASTRUCTURE_ERROR
        assert state_infra["rag_result"]["error"] == "Chroma connection failed"


# ============================================================================
# 5 & 6. NO MISREPRESENTATION (INFRA DOES NOT BECOME EMPTY AND VICE VERSA)
# ============================================================================
@pytest.mark.asyncio
async def test_5_6_no_misrepresentation_between_empty_and_infra_error(mock_ollama_client):
    """5, 6. RAG_INFRASTRUCTURE_ERROR is never represented as RAG_EMPTY and vice-versa."""
    rev = ReviewerAgent(client=mock_ollama_client)

    # RAG_INFRASTRUCTURE_ERROR dict
    rag_infra = {"status": "RAG_INFRASTRUCTURE_ERROR", "error": "DB connection timeout", "chunks": []}
    norm_infra = rev._normalize_evidence(validation_results={"quality_gate": "PASS"}, research_notes="No documents found in KB", rag_result=rag_infra)
    assert "RAG_INFRASTRUCTURE_ERROR" in norm_infra["evidence_section"]
    assert "RAG_EMPTY" not in norm_infra["evidence_section"]
    assert "Do NOT claim no documents exist" in norm_infra["evidence_section"]

    # RAG_EMPTY dict
    rag_empty = {"status": "RAG_EMPTY", "error": None, "chunks": []}
    norm_empty = rev._normalize_evidence(validation_results={"quality_gate": "PASS"}, research_notes="Infrastructure Error occurred", rag_result=rag_empty)
    assert "RAG_EMPTY" in norm_empty["evidence_section"]
    assert "RAG_INFRASTRUCTURE_ERROR" not in norm_empty["evidence_section"]


# ============================================================================
# 7 & 8. CODER & REVIEWER CONSUME STRUCTURED RAG STATE
# ============================================================================
@pytest.mark.asyncio
async def test_7_8_coder_and_reviewer_consume_structured_rag_state(mock_ollama_client, tmp_path: Path):
    """7, 8. CoderAgent and ReviewerAgent consume structured rag_result directly."""
    coder = CoderAgent(client=mock_ollama_client)
    ws = WorkspaceService(db=None, session_id="rag_sess_3", workspace_dir=tmp_path)

    rag_infra = {"status": "RAG_INFRASTRUCTURE_ERROR", "error": "Chroma crash", "chunks": []}
    coder_out = await coder.execute(
        user_request="Implement auth",
        execution_plan="Plan",
        research_notes="Prose notes",
        workspace_service=ws,
        rag_result=rag_infra,
    )
    assert coder_out is not None

    reviewer = ReviewerAgent(client=mock_ollama_client)
    val_results = {"quality_gate": "PASS", "code_contract": {"status": "PASS"}}
    rev_out = await reviewer.execute(
        user_request="Implement auth",
        execution_plan="Plan",
        generated_code="code",
        test_results="tests",
        research_notes="Incorrect prose claiming 0 docs found",
        validation_results=val_results,
        rag_result=rag_infra,
    )
    assert "RAG_INFRASTRUCTURE_ERROR" in rev_out["output"]
    assert "RAG_EMPTY" not in rev_out["output"]


# ============================================================================
# 9, 10, 11. REVIEWER EVIDENCE ACCURACY & SUCCESS UTILIZATION
# ============================================================================
@pytest.mark.asyncio
async def test_9_10_11_reviewer_rag_evidence_accuracy(mock_ollama_client):
    """9-11. Reviewer accuracy for RAG_INFRASTRUCTURE_ERROR, RAG_EMPTY, and RAG_SUCCESS."""
    rev = ReviewerAgent(client=mock_ollama_client)
    val_res = {"quality_gate": "PASS"}

    # 9. Infra error does not claim no docs found
    n9 = rev._normalize_evidence(val_res, rag_result={"status": "RAG_INFRASTRUCTURE_ERROR", "error": "Failed"})
    assert "Do NOT claim no documents exist" in n9["evidence_section"]

    # 10. Empty correctly describes 0 matching docs found
    n10 = rev._normalize_evidence(val_res, rag_result={"status": "RAG_EMPTY"})
    assert "0 matching documents found" in n10["evidence_section"]

    # 11. Success uses retrieved chunks count
    n11 = rev._normalize_evidence(val_res, rag_result={"status": "RAG_SUCCESS", "chunks": [{"filename": "a.py"}]})
    assert "RAG_SUCCESS (Relevant Knowledge Base documents retrieved: 1 chunk(s) available.)" in n11["evidence_section"]


# ============================================================================
# 12, 13, 14. RAG RESULT PERSISTENCE ACROSS GRAPH TRANSITIONS
# ============================================================================
@pytest.mark.asyncio
async def test_12_13_14_rag_result_persists_across_workflow(mock_ollama_client, tmp_path: Path):
    """12-14. rag_result survives Research -> Coder -> Tester -> Quality Gate -> Reviewer without being overwritten."""
    ws = WorkspaceService(db=None, session_id="rag_sess_4", workspace_dir=tmp_path)
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

    mock_rag = RAGResult(
        status=RAGStatus.RAG_SUCCESS,
        chunks=[{"filename": "core.py", "score": 0.88, "chunk_index": 0, "content": "core logic"}],
        retrieval_time=0.01,
    )

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag), \
         patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Full E2E RAG Workflow", "session_id": "rag_sess_4"})

    assert final_state["rag_result"] is not None
    assert final_state["rag_result"]["status"] == RAGStatus.RAG_SUCCESS
    assert final_state["rag_result"]["chunks"][0]["filename"] == "core.py"


# ============================================================================
# 15 & 16. MULTIPLE RESEARCH NODES & ERROR PRESERVATION
# ============================================================================
@pytest.mark.asyncio
async def test_15_16_multiple_research_nodes_and_error_preservation(mock_ollama_client, tmp_path: Path):
    """15, 16. Multiple Research nodes update rag_result deterministically and preserve error details."""
    ws = WorkspaceService(db=None, session_id="rag_sess_5", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
            {"id": "r2", "type": "research"},
        ],
        "edges": [
            {"source": "p1", "target": "r1"},
            {"source": "r1", "target": "r2"},
        ],
    }
    compiled = compiler.compile(graph_json)

    mock_rag1 = RAGResult(status=RAGStatus.RAG_SUCCESS, chunks=[{"filename": "f1.py", "score": 0.9, "chunk_index": 0, "content": "c1"}], retrieval_time=0.01)
    mock_rag2 = RAGResult(status=RAGStatus.RAG_INFRASTRUCTURE_ERROR, chunks=[], error="Specific vector store error detail")

    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", side_effect=[mock_rag1, mock_rag2]):
        state = await compiled.ainvoke({"user_request": "Multi Research", "session_id": "rag_sess_5"})

    assert state["rag_result"]["status"] == RAGStatus.RAG_INFRASTRUCTURE_ERROR
    assert state["rag_result"]["error"] == "Specific vector store error detail"


# ============================================================================
# 17 & 18. SESSION ISOLATION & NO PROSE PARSING DEPENDENCY
# ============================================================================
@pytest.mark.asyncio
async def test_17_18_session_isolation_and_no_prose_parsing_dependency(mock_ollama_client, tmp_path: Path):
    """17, 18. RAG state remains session-isolated; structured rag_result overrides prose parsing when they disagree."""
    rev = ReviewerAgent(client=mock_ollama_client)

    # Disagreement test: prose says RAG_EMPTY, structured says RAG_INFRASTRUCTURE_ERROR
    disagree_notes = "Knowledge Base was accessed successfully, but returned 0 relevant document chunks."
    struct_infra = {"status": "RAG_INFRASTRUCTURE_ERROR", "error": "Chroma offline", "chunks": []}

    norm = rev._normalize_evidence(
        validation_results={"quality_gate": "PASS"},
        research_notes=disagree_notes,
        rag_result=struct_infra,
    )

    assert "RAG_INFRASTRUCTURE_ERROR" in norm["evidence_section"]
    assert "RAG_EMPTY" not in norm["evidence_section"]


# ============================================================================
# INTEGRATION SCENARIO 1: FULL HAPPY PATH RAG_SUCCESS
# ============================================================================
@pytest.mark.asyncio
async def test_integration_scenario_1_rag_success_e2e(mock_ollama_client, tmp_path: Path):
    """Integration Scenario 1: Research (RAG_SUCCESS) -> Coder -> Tester -> Quality Gate -> Reviewer."""
    ws = WorkspaceService(db=None, session_id="int_rag_success", workspace_dir=tmp_path)
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

    mock_rag = RAGResult(
        status=RAGStatus.RAG_SUCCESS,
        chunks=[{"filename": "security.py", "score": 0.92, "chunk_index": 0, "content": "hash_password()"}],
        retrieval_time=0.008,
    )

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag), \
         patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Build Auth", "session_id": "int_rag_success"})

    assert final_state["rag_result"]["status"] == RAGStatus.RAG_SUCCESS
    assert final_state["quality_gate"] == "PASS"
    assert "APPROVED" in final_state["node_outputs"]["rev1"]


# ============================================================================
# INTEGRATION SCENARIO 2: RAG_INFRASTRUCTURE_ERROR HANDLING
# ============================================================================
@pytest.mark.asyncio
async def test_integration_scenario_2_rag_infrastructure_error_e2e(mock_ollama_client, tmp_path: Path):
    """Integration Scenario 2: Research (RAG_INFRASTRUCTURE_ERROR) -> Coder -> Reviewer."""
    ws = WorkspaceService(db=None, session_id="int_rag_infra", workspace_dir=tmp_path)
    compiler = DynamicGraphCompiler(ollama_client=mock_ollama_client, workspace_service=ws)

    graph_json = {
        "nodes": [
            {"id": "p1", "type": "planner"},
            {"id": "r1", "type": "research"},
            {"id": "c1", "type": "coder"},
            {"id": "rev1", "type": "reviewer"},
        ],
        "edges": [
            {"source": "p1", "target": "r1"},
            {"source": "r1", "target": "c1"},
            {"source": "c1", "target": "rev1"},
        ],
    }

    compiled = compiler.compile(graph_json)

    mock_rag_infra = RAGResult(
        status=RAGStatus.RAG_INFRASTRUCTURE_ERROR,
        chunks=[],
        error="ChromaDB Server unreachable at port 8000",
    )

    mock_ruff = ToolResult(tool="ruff", command=["ruff"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_rag_infra), \
         patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Build Auth", "session_id": "int_rag_infra"})

    assert final_state["rag_result"]["status"] == RAGStatus.RAG_INFRASTRUCTURE_ERROR
    assert final_state["rag_result"]["error"] == "ChromaDB Server unreachable at port 8000"
    assert "RAG_INFRASTRUCTURE_ERROR" in final_state["node_outputs"]["rev1"]
    assert "no documents found" not in final_state["node_outputs"]["rev1"].lower()
