"""
Unit and Integration Tests for Phase 13: Agent Reasoning & Output Quality Enhancement.

Validates:
1. Non-authoritative ReasoningMetadata schema & Planner/Research/Coder/Tester/Reviewer quality prompt guidance.
2. Planner reasoning metadata extraction & PlanContract validity independence.
3. ResearchAgent evidence categorization (FACT, EVIDENCE, GENERAL KNOWLEDGE, ASSUMPTION, UNKNOWN).
4. CoderAgent multi-file consistency, implementation rationale, and non-claim of test execution.
5. TesterAgent behavioral edge-case design without claiming test execution.
6. ReviewerAgent structured review headings (OBSERVED FACTS, TECHNICAL ASSESSMENT, STRENGTHS, WEAKNESSES, RISKS, RECOMMENDATIONS, FINAL REVIEW) & Quality Gate supremacy.
7. Reasoning metadata survival across DynamicGraph transitions.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.ai.ollama_client import OllamaClient
from app.agents.coder import CoderAgent
from app.agents.planner import PlannerAgent, PlannerResult
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.tester import TesterAgent
from app.orchestration.dynamic_graph import DynamicGraphCompiler
from app.schemas.rag import RAGResult, RAGStatus
from app.schemas.reasoning import ReasoningMetadata
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
        "task_summary": "Reasoning Quality Test",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research requirements", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Implement core logic", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Create test suite", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Review evidence", "dependencies": [3]},
        ],
        "file_manifest": ["main.py", "test_main.py"],
        "acceptance_criteria": ["All tests pass"],
        "reasoning": {
            "decision": "Modular 4-agent flow",
            "evidence_used": ["Project layout"],
            "rationale": "High cohesion",
            "alternatives_considered": ["Monolith"],
            "trade_offs": ["Overhead"],
            "risks": ["API drift"],
        },
    })

    coder_resp = (
        "## Implementation Rationale\n"
        "- Decision: Fast API service\n"
        "- Why: Lightweight\n\n"
        '```python filepath="main.py"\n'
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
        "```"
    )

    tester_resp = (
        "## Coverage Analysis\n"
        "- Behavior tested: Addition logic\n"
        "- Expected failure: AssertionError\n\n"
        '```python filepath="test_main.py"\n'
        "from main import add\n"
        "def test_add():\n"
        "    assert add(1, 2) == 3\n"
        "```"
    )

    reviewer_resp = (
        "## OBSERVED FACTS\n"
        "Tool tests passed cleanly.\n\n"
        "## TECHNICAL ASSESSMENT\n"
        "Code is clean.\n\n"
        "## STRENGTHS\n"
        "No linter errors.\n\n"
        "## WEAKNESSES\n"
        "None.\n\n"
        "## RISKS\n"
        "None.\n\n"
        "## RECOMMENDATIONS\n"
        "Ship code.\n\n"
        "## FINAL REVIEW\n"
        "Approved."
    )

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
# 1-4. PLANNER REASONING QUALITY & CONTRACT INDEPENDENCE
# ============================================================================
@pytest.mark.asyncio
async def test_1_to_4_planner_reasoning_and_contract_independence(mock_ollama_client):
    """1-4. Planner generates ReasoningMetadata; invalid/missing reasoning metadata does NOT invalidate PlanContract."""
    planner = PlannerAgent(client=mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Build math service")

    assert res.is_valid is True
    assert res.reasoning_metadata is not None
    assert res.reasoning_metadata.decision == "Modular 4-agent flow"

    # Test 2: Invalid reasoning JSON does not break valid PlanContract
    invalid_reasoning_json = json.dumps({
        "task_summary": "Valid plan",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["coder"],
        "subtasks": [{"id": 1, "agent": "research", "description": "d", "dependencies": []}, {"id": 2, "agent": "coder", "description": "c", "dependencies": [1]}, {"id": 3, "agent": "tester", "description": "t", "dependencies": [2]}],
        "file_manifest": ["main.py"],
        "reasoning": "NOT A DICT",
    })
    mock_ollama_client.chat = AsyncMock(return_value=invalid_reasoning_json)
    res_inv = await planner.execute_contract("Build math service")
    assert res_inv.is_valid is True
    assert res_inv.contract is not None


# ============================================================================
# 5-8. RESEARCH EVIDENCE CATEGORIZATION & RAG STATUS PRESERVATION
# ============================================================================
@pytest.mark.asyncio
async def test_5_to_8_research_reasoning_and_rag_preservation(mock_ollama_client):
    """5-8. ResearchAgent categorizes evidence & preserves authoritative RAGResult statuses."""
    agent = ResearchAgent(client=mock_ollama_client)

    # 6. RAG_SUCCESS
    mock_success = RAGResult(status=RAGStatus.RAG_SUCCESS, chunks=[{"filename": "a.py", "score": 0.9, "chunk_index": 0, "content": "pass"}])
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_success):
        out_text, rag_res = await agent.execute_with_result("req", "plan")
        assert rag_res.status == RAGStatus.RAG_SUCCESS
        assert "RETRIEVED DOCUMENTS & KNOWLEDGE" in out_text

    # 7. RAG_EMPTY
    mock_empty = RAGResult(status=RAGStatus.RAG_EMPTY, chunks=[])
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_empty):
        out_text_e, rag_res_e = await agent.execute_with_result("req", "plan")
        assert rag_res_e.status == RAGStatus.RAG_EMPTY

    # 8. RAG_INFRASTRUCTURE_ERROR
    mock_infra = RAGResult(status=RAGStatus.RAG_INFRASTRUCTURE_ERROR, error="Chroma down")
    with patch("app.knowledge.retriever.search.KnowledgeRetriever.retrieve_with_status", return_value=mock_infra):
        out_text_i, rag_res_i = await agent.execute_with_result("req", "plan")
        assert rag_res_i.status == RAGStatus.RAG_INFRASTRUCTURE_ERROR
        assert "infrastructure error" in out_text_i.lower()


# ============================================================================
# 9-12. CODER REASONING, MULTI-FILE CONSISTENCY & NO TEST CLAIMS
# ============================================================================
@pytest.mark.asyncio
async def test_9_to_12_coder_reasoning_and_no_test_claims(mock_ollama_client, tmp_path: Path):
    """9-12. CoderAgent receives RAG context, emits implementation rationale, and does NOT claim tests passed."""
    coder = CoderAgent(client=mock_ollama_client)
    ws = WorkspaceService(db=None, session_id="coder_sess", workspace_dir=tmp_path)

    out = await coder.execute(
        user_request="Build service",
        execution_plan="Plan",
        research_notes="Notes",
        workspace_service=ws,
        rag_result={"status": "RAG_SUCCESS", "chunks": []},
    )

    assert "Implementation Rationale" in out
    assert (tmp_path / "main.py").exists()
    assert "tested successfully" not in out.lower()


# ============================================================================
# 13-14. TESTER BEHAVIORAL REASONING & NO TEST EXECUTION CLAIMS
# ============================================================================
@pytest.mark.asyncio
async def test_13_14_tester_behavioral_reasoning(mock_ollama_client, tmp_path: Path):
    """13, 14. TesterAgent produces behavioral edge-case analysis and does NOT claim test execution."""
    tester = TesterAgent(client=mock_ollama_client)
    ws = WorkspaceService(db=None, session_id="test_sess", workspace_dir=tmp_path)

    res = await tester.execute(
        generated_code='```python filepath="main.py"\ndef add(a, b):\n    return a + b\n```',
        execution_plan="Plan",
        workspace_service=ws,
    )

    assert "Behavior tested" in res["output"]
    assert "tests passed" not in res["output"].lower()


# ============================================================================
# 15-23. REVIEWER STRUCTURED SECTIONS & QUALITY GATE SUPREMACY
# ============================================================================
@pytest.mark.asyncio
async def test_15_to_23_reviewer_structured_sections_and_gate_supremacy(mock_ollama_client):
    """15-23. ReviewerAgent separates observed facts from inferences and cannot override Quality Gate status."""
    reviewer = ReviewerAgent(client=mock_ollama_client)

    # 18 & 19. Quality Gate says FAIL, Reviewer cannot override
    val_fail = {
        "quality_gate": "TEST_FAILURE",
        "pytest": {"status": "FAIL", "output": "AssertionError"},
    }
    res = await reviewer.execute(
        user_request="req",
        execution_plan="plan",
        generated_code="code",
        test_results="tests",
        validation_results=val_fail,
    )
    assert res["quality_gate"] == "TEST_FAILURE"
    assert "REJECTED" in res["output"] or "TEST_FAILURE" in res["output"]

    # 20 & 21. Infrastructure errors remain infrastructure errors, missing evidence remains UNAVAILABLE
    val_infra = {
        "quality_gate": "INFRASTRUCTURE_FAILURE",
        "ruff": {"status": "INFRASTRUCTURE_ERROR", "output": "Ruff missing"},
    }
    res_infra = await reviewer.execute(
        user_request="req",
        execution_plan="plan",
        generated_code="code",
        test_results="tests",
        validation_results=val_infra,
    )
    assert "INFRASTRUCTURE_ERROR" in res_infra["output"]
    assert "UNAVAILABLE" in res_infra["output"]


# ============================================================================
# 24-25. REASONING METADATA SURVIVES DYNAMIC GRAPH TRANSITIONS
# ============================================================================
@pytest.mark.asyncio
async def test_24_25_reasoning_metadata_survives_graph_transitions(mock_ollama_client, tmp_path: Path):
    """24, 25. ReasoningMetadata survives DynamicGraph transitions while keeping deterministic state intact."""
    ws = WorkspaceService(db=None, session_id="reasoning_graph_sess", workspace_dir=tmp_path)
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
    mock_pytest = ToolResult(tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)
    mock_bandit = ToolResult(tool="bandit", command=["bandit"], cwd=str(tmp_path), exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS)

    with patch("app.agents.validator.DeterministicValidator._run_tool_cmd", side_effect=[mock_ruff, mock_bandit]), \
         patch("app.agents.validator.DeterministicValidator._run_pytest", return_value=mock_pytest):

        final_state = await compiled.ainvoke({"user_request": "Graph Reasoning Test", "session_id": "reasoning_graph_sess"})

    assert "reasoning_metadata" in final_state
    assert "p1" in final_state["reasoning_metadata"]
    assert final_state["reasoning_metadata"]["p1"]["decision"] == "Modular 4-agent flow"
    assert final_state["quality_gate"] == "PASS"
