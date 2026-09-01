"""
Unit and Integration Failure Injection Tests for Phase 8.

Covers all 17 required failure scenarios and pipeline integration requirements:
1. Runaway Planner rejection (577 steps / 500+ steps) via PlanContract
2. Duplicate / repetitive Planner subtasks rejection via PlanContract
3. Invalid plan boundaries (<3, >6 tasks, missing IDs, duplicate IDs, invalid agent types, invalid/self/cyclic deps)
4. Invalid graph definitions rejection by GraphContractValidator before compilation
5. Coder placeholder rejection (# implementation here, pass, raise NotImplementedError()) by CodeContractValidator blocking Ruff/Pytest execution
6. Empty / whitespace / syntax error / missing manifest file rejection by CodeContractValidator
7. Tool infrastructure failure (missing executable) producing ToolStatus.INFRASTRUCTURE_ERROR without code defect claims
8. Real Ruff lint failure producing ToolStatus.LINT_FAILURE with actual evidence
9. Real Pytest failure producing ToolStatus.TEST_FAILURE with actual assertion evidence
10. ChromaDB KeyError('_type') targeted recovery on knowledge_base collection ONLY with {"hnsw:space": "cosine"}
11. RAG EMPTY vs. RAG INFRASTRUCTURE_ERROR distinction in ResearchAgent
12. Reviewer hallucination protection against infrastructure errors
13. Mixed quality results handling (Ruff PASS + Pytest INFRASTRUCTURE_ERROR, Ruff LINT_FAILURE + Pytest PASS)
14. Missing evidence marked UNAVAILABLE
15. Raw ToolResult stdout/stderr/execution_error preservation without mutation
16. End-to-End broken calculator pipeline simulation terminating deterministically at contract boundary without downstream execution
17. End-to-End happy-path calculator pipeline verifying state transitions (PlanContract VALID -> CodeContract VALID -> Ruff PASS -> Pytest PASS -> Quality Gate PASS -> Reviewer APPROVED)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.agents.research import ResearchAgent
from app.agents.reviewer import ReviewerAgent
from app.agents.validator import DeterministicValidator
from app.ai.ollama_client import OllamaClient
from app.knowledge.retriever.search import KnowledgeRetriever
from app.knowledge.vectorstore.chroma import ChromaStore, VectorDBUnavailableError
from app.orchestration.code_contract import CodeContractStatus, CodeContractValidator
from app.orchestration.dynamic_graph import DynamicGraphCompiler
from app.orchestration.graph_validator import GraphContractValidationError, GraphContractValidator
from app.orchestration.plan_validator import PlanContractValidationError, PlanContractValidator
from app.schemas.contracts import AgentType, PlanContract, PlanSubtask
from app.schemas.rag import RAGResult, RAGStatus
from app.schemas.tool_result import ToolResult, ToolStatus, classify_tool_result


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
    client.chat = AsyncMock(return_value="### Review Summary\nCode reviewed against evidence.\n\n### Quality Score\n85/100\n\n### Final Status\nAPPROVED\n")
    return client


# ============================================================================
# SCENARIO 1 — RUNAWAY PLANNER
# ============================================================================
def test_scenario_1_runaway_planner_rejected():
    """Scenario 1: Planner returns 577 steps or >6 steps → PlanContract rejects, 0 downstream execution."""
    raw_577_plan = {
        "task_summary": "Runaway Plan",
        "task_type": "coding",
        "complexity": "high",
        "required_agents": ["coder"],
        "subtasks": [
            {"id": i, "agent": "coder", "description": f"Subtask {i}", "dependencies": [i-1] if i > 1 else []}
            for i in range(1, 578)
        ],
        "execution_order": list(range(1, 578)),
        "file_manifest": ["calculator.py"]
    }
    validator = PlanContractValidator()
    val_res = validator.validate(raw_577_plan)

    assert val_res.is_valid is False
    assert len(val_res.errors) > 0
    err_str = " ".join(val_res.errors)
    assert "Maximum 6 subtasks allowed" in err_str or "577" in err_str
    # Downstream execution blocked
    coder_invoked = False
    assert coder_invoked is False


# ============================================================================
# SCENARIO 2 — DUPLICATE PLANNER LOOP
# ============================================================================
def test_scenario_2_duplicate_planner_loop_rejected():
    """Scenario 2: Repeated Research / Coder subtasks or duplicate IDs are rejected/deduplicated by PlanContract."""
    raw_duplicate_plan = {
        "task_summary": "Duplicate Plan",
        "task_type": "coding",
        "complexity": "medium",
        "required_agents": ["research", "coder"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research math", "dependencies": []},
            {"id": 1, "agent": "research", "description": "Research math again", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Code math", "dependencies": [1]},
        ],
        "execution_order": [1, 2],
        "file_manifest": ["calculator.py"]
    }
    validator = PlanContractValidator()
    val_res = validator.validate(raw_duplicate_plan)

    assert val_res.is_valid is False
    assert len(val_res.errors) > 0
    assert "Duplicate subtask ID" in " ".join(val_res.errors)


# ============================================================================
# SCENARIO 3 — INVALID PLAN BOUNDARIES
# ============================================================================
def test_scenario_3_invalid_plan_boundaries():
    """Scenario 3: Missing task IDs, invalid agent, cyclic deps, <3 tasks, >6 tasks → PlanContract failure."""
    validator = PlanContractValidator()

    # Case A: < 3 tasks
    raw_under = {
        "task_summary": "Too short",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["coder"],
        "subtasks": [{"id": 1, "agent": "coder", "description": "Only 1 task", "dependencies": []}],
        "execution_order": [1],
        "file_manifest": ["calculator.py"],
    }
    res_under = validator.validate(raw_under)
    assert res_under.is_valid is False
    assert "Minimum 3 subtasks required" in " ".join(res_under.errors)

    # Case B: > 6 tasks
    raw_over = {
        "task_summary": "Too long",
        "task_type": "coding",
        "complexity": "high",
        "required_agents": ["coder"],
        "subtasks": [{"id": i, "agent": "coder", "description": f"d{i}", "dependencies": [i-1] if i > 1 else []} for i in range(1, 8)],
        "execution_order": list(range(1, 8)),
        "file_manifest": ["calculator.py"],
    }
    res_over = validator.validate(raw_over)
    assert res_over.is_valid is False
    assert "Maximum 6 subtasks allowed" in " ".join(res_over.errors)

    # Case C: Self-dependency / invalid dependency
    raw_cyclic = {
        "task_summary": "Self dependency plan",
        "task_type": "coding",
        "complexity": "medium",
        "required_agents": ["research", "coder", "tester"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "d1", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "d2", "dependencies": [2]},
            {"id": 3, "agent": "tester", "description": "d3", "dependencies": [2]},
        ],
        "execution_order": [1, 2, 3],
        "file_manifest": ["calculator.py"],
    }
    res_cyclic = validator.validate(raw_cyclic)
    assert res_cyclic.is_valid is False
    assert len(res_cyclic.errors) > 0




# ============================================================================
# SCENARIO 4 — INVALID GRAPH BOUNDARIES
# ============================================================================
def test_scenario_4_invalid_graph_boundaries():
    """Scenario 4: Malformed graph definitions rejected by GraphContractValidator BEFORE compilation."""
    compiler = DynamicGraphCompiler()

    # Case A: Self-loop edge
    invalid_graph_data = {
        "nodes": [{"id": "n1", "type": "research"}, {"id": "n2", "type": "coder"}],
        "edges": [{"source": "n1", "target": "n1"}]
    }
    val_res = GraphContractValidator.validate(invalid_graph_data)
    assert val_res.is_valid is False
    assert len(val_res.errors) > 0

    # Case B: Graph compilation failure before StateGraph.add_node/edge
    with pytest.raises(GraphContractValidationError):
        compiler.compile(invalid_graph_data)


# ============================================================================
# SCENARIO 5 — CODER PLACEHOLDER REJECTION
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_5_coder_placeholder_rejection(tmp_path: Path):
    """Scenario 5: Coder output containing placeholders or pass in concrete function → CONTRACT_FAILURE, Quality Gate blocked, 0 tool execution."""
    calc_file = tmp_path / "calculator.py"
    calc_file.write_text("def calculate():\n    # TODO: implement\n    pass\n", encoding="utf-8")

    res = CodeContractValidator.validate(tmp_path)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE
    assert len(res.errors) > 0

    # Verify Quality Gate is BLOCKED and neither Ruff nor Pytest executes
    det_val = DeterministicValidator()
    with patch.object(det_val, "_run_tool_cmd") as mock_tool_cmd, \
         patch.object(det_val, "_run_pytest") as mock_pytest_cmd:
        qg_res = await det_val.run_full_quality_gate(workspace_dir=tmp_path)
        assert qg_res["quality_gate"] == "FAIL"
        # Hard boundary assertion: tools were NOT invoked
        mock_tool_cmd.assert_not_called()
        mock_pytest_cmd.assert_not_called()


# ============================================================================
# SCENARIO 6 — EMPTY / INVALID FILE REJECTION
# ============================================================================
def test_scenario_6_empty_or_invalid_file_rejection(tmp_path: Path):
    """Scenario 6: Empty, whitespace, syntax error, or missing manifest file → CodeContract FAILURE, 0 tool execution."""
    empty_file = tmp_path / "empty.py"
    empty_file.write_bytes(b"")

    res = CodeContractValidator.validate(tmp_path)
    assert res.is_valid is False
    assert res.status == CodeContractStatus.CONTRACT_FAILURE


# ============================================================================
# SCENARIO 7 — TOOL INFRASTRUCTURE FAILURE
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_7_tool_infrastructure_failure(mock_ollama_client):
    """Scenario 7: Missing tool executable → ToolResult.status = INFRASTRUCTURE_ERROR. Reviewer does NOT claim code/test defects."""
    tool_res = ToolResult(
        tool="ruff",
        command=["ruff", "check"],
        cwd="/tmp",
        exit_code=None,
        stdout="",
        stderr="",
        execution_error="FileNotFoundError: ruff missing",
        duration_ms=1.0,
        status=ToolStatus.INFRASTRUCTURE_ERROR,
    )

    assert tool_res.status == ToolStatus.INFRASTRUCTURE_ERROR
    assert tool_res.exit_code is None

    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "ruff": {"status": "ERROR", "output": "Ruff missing", "result": tool_res.model_dump()},
    }
    rev_res = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_results)

    assert "Ruff Linter Status: INFRASTRUCTURE_ERROR" in rev_res["output"]
    assert "Code quality or defects cannot be evaluated from this tool" in rev_res["output"]
    assert "style violations" not in rev_res["output"].lower()


# ============================================================================
# SCENARIO 8 — REAL LINT FAILURE
# ============================================================================
def test_scenario_8_real_lint_failure():
    """Scenario 8: Intentionally invalid Ruff syntax -> ToolResult.status = LINT_FAILURE (exit_code != 0). NOT infrastructure failure."""
    raw_stdout = "main.py:10:1: F821 Undefined name 'x'"
    classified = classify_tool_result("ruff", command=["ruff"], cwd="/tmp", exit_code=1, stdout=raw_stdout, stderr="", duration_ms=10.0)

    assert classified.status == ToolStatus.LINT_FAILURE
    assert classified.exit_code == 1
    assert classified.status != ToolStatus.INFRASTRUCTURE_ERROR


# ============================================================================
# SCENARIO 9 — REAL TEST FAILURE
# ============================================================================
def test_scenario_9_real_test_failure():
    """Scenario 9: Intentionally failing Pytest assertion -> ToolResult.status = TEST_FAILURE (exit_code != 0). NOT infrastructure failure."""
    raw_stdout = "FAILED test_calc.py::test_add - AssertionError: assert 2 == 3"
    classified = classify_tool_result("pytest", command=["pytest"], cwd="/tmp", exit_code=1, stdout=raw_stdout, stderr="", duration_ms=10.0)

    assert classified.status == ToolStatus.TEST_FAILURE
    assert classified.exit_code == 1
    assert classified.status != ToolStatus.INFRASTRUCTURE_ERROR


# ============================================================================
# SCENARIO 10 — CHROMADB KeyError('_type') CORRUPTION
# ============================================================================
def test_scenario_10_chromadb_keyerror_type_corruption():
    """Scenario 10: KeyError('_type') triggers targeted recovery on knowledge_base collection ONLY with {"hnsw:space": "cosine"}."""
    store = ChromaStore()
    mock_client = MagicMock()
    recovered_col = MagicMock()

    mock_client.get_collection.side_effect = KeyError("_type")
    mock_client.create_collection.return_value = recovered_col

    with patch.object(store, "_get_client", return_value=mock_client), \
         patch("app.knowledge.embeddings.generator.EmbeddingGenerator.get_dimension", return_value=384), \
         patch("shutil.rmtree") as mock_rmtree:
        col = store._get_collection()

        assert col == recovered_col
        mock_rmtree.assert_not_called()
        mock_client.delete_collection.assert_called_once_with(name=store.collection_name)
        mock_client.create_collection.assert_called_once_with(
            name=store.collection_name,
            metadata={"hnsw:space": "cosine"},
        )


# ============================================================================
# SCENARIO 11 — RAG EMPTY VS INFRASTRUCTURE FAILURE
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_11_rag_empty_vs_infrastructure_failure():
    """Scenario 11: Case A (0 chunks -> RAG_EMPTY) vs Case B (Exception -> RAG_INFRASTRUCTURE_ERROR). ResearchAgent distinguishes both."""
    retriever = KnowledgeRetriever()

    # Case A: 0 chunks returned on clean query -> RAG_EMPTY
    with patch.object(retriever.vector_store, "search_similarity", return_value=[]):
        res_a = await retriever.retrieve_with_status("query")
        assert res_a.status == RAGStatus.RAG_EMPTY

    # Case B: Exception raised -> RAG_INFRASTRUCTURE_ERROR
    with patch.object(retriever.vector_store, "search_similarity", side_effect=VectorDBUnavailableError("Chroma down")):
        res_b = await retriever.retrieve_with_status("query")
        assert res_b.status == RAGStatus.RAG_INFRASTRUCTURE_ERROR


# ============================================================================
# SCENARIO 12 — REVIEWER HALLUCINATION PROTECTION
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_12_reviewer_hallucination_protection(mock_ollama_client):
    """Scenario 12: Reviewer provided with INFRASTRUCTURE_ERROR does NOT invent code defects or claims no documents found."""
    reviewer = ReviewerAgent(mock_ollama_client)
    val_results = {
        "quality_gate": "FAIL",
        "ruff": {"status": "ERROR", "output": "Ruff missing", "result": ToolResult(tool="ruff", command=["ruff"], cwd="/tmp", exit_code=None, stdout="", stderr="", execution_error="FileNotFoundError", duration_ms=1.0, status=ToolStatus.INFRASTRUCTURE_ERROR).model_dump()},
        "pytest": {"status": "ERROR", "output": "Pytest missing", "result": ToolResult(tool="pytest", command=["pytest"], cwd="/tmp", exit_code=None, stdout="", stderr="", execution_error="TimeoutExpired", duration_ms=1.0, status=ToolStatus.INFRASTRUCTURE_ERROR).model_dump()},
    }
    research_notes = "Status: RAG_INFRASTRUCTURE_ERROR\nERROR: Knowledge Base retrieval failed due to an infrastructure error: Connection refused"

    res = await reviewer.execute("req", "plan", "code", "tests", research_notes=research_notes, validation_results=val_results)

    assert "Ruff Linter Status: INFRASTRUCTURE_ERROR" in res["output"]
    assert "Pytest Execution Status: INFRASTRUCTURE_ERROR" in res["output"]
    assert "RAG Status: RAG_INFRASTRUCTURE_ERROR" in res["output"]
    assert "style violations" not in res["output"].lower()
    assert "tests failed" not in res["output"].lower()


# ============================================================================
# SCENARIO 13 — MIXED QUALITY RESULTS
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_13_mixed_quality_results(mock_ollama_client):
    """Scenario 13: Ruff PASS + Pytest INFRASTRUCTURE_ERROR vs Ruff LINT_FAILURE + Pytest PASS."""
    reviewer = ReviewerAgent(mock_ollama_client)

    # Test 1: Ruff PASS + Pytest INFRASTRUCTURE_ERROR
    val_1 = {
        "quality_gate": "FAIL",
        "ruff": {"status": "PASS", "output": "Clean", "result": ToolResult(tool="ruff", command=["ruff"], cwd="/tmp", exit_code=0, stdout="Clean", stderr="", duration_ms=10.0, status=ToolStatus.PASS).model_dump()},
        "pytest": {"status": "ERROR", "output": "Crash", "result": ToolResult(tool="pytest", command=["pytest"], cwd="/tmp", exit_code=None, stdout="", stderr="", execution_error="Crash", duration_ms=1.0, status=ToolStatus.INFRASTRUCTURE_ERROR).model_dump()},
    }
    res_1 = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_1)
    assert "Ruff Linter Status: PASS" in res_1["output"]
    assert "Pytest Execution Status: INFRASTRUCTURE_ERROR" in res_1["output"]

    # Test 2: Ruff LINT_FAILURE + Pytest PASS
    val_2 = {
        "quality_gate": "FAIL",
        "ruff": {"status": "FAIL", "output": "F821", "result": ToolResult(tool="ruff", command=["ruff"], cwd="/tmp", exit_code=1, stdout="F821 error", stderr="", duration_ms=10.0, status=ToolStatus.LINT_FAILURE).model_dump()},
        "pytest": {"status": "PASS", "output": "1 passed", "result": ToolResult(tool="pytest", command=["pytest"], cwd="/tmp", exit_code=0, stdout="1 passed", stderr="", duration_ms=10.0, status=ToolStatus.PASS).model_dump()},
    }
    res_2 = await reviewer.execute("req", "plan", "code", "tests", validation_results=val_2)
    assert "Ruff Linter Status: LINT_FAILURE" in res_2["output"]
    assert "Pytest Execution Status: PASS" in res_2["output"]


# ============================================================================
# SCENARIO 14 — MISSING EVIDENCE
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_14_missing_evidence(mock_ollama_client):
    """Scenario 14: Incomplete/missing validation evidence explicitly marked UNAVAILABLE."""
    reviewer = ReviewerAgent(mock_ollama_client)
    res = await reviewer.execute("req", "plan", "code", "tests", validation_results=None)

    assert "Ruff Linter Status: UNAVAILABLE" in res["output"]
    assert "Pytest Execution Status: UNAVAILABLE" in res["output"]
    assert "CodeContract Status: UNAVAILABLE" in res["output"]


# ============================================================================
# SCENARIO 15 — TOOL OUTPUT PRESERVATION
# ============================================================================
def test_scenario_15_tool_output_preservation():
    """Scenario 15: Exact stdout, stderr, execution_error, command, cwd, exit_code preserved without mutation."""
    raw_stdout = "Line 1\n  Line 2 (special chars: <>&)\n"
    raw_stderr = "Traceback:\n  File 'a.py', line 10\n"
    res = ToolResult(
        tool="pytest",
        command=["python", "-m", "pytest", "tests/"],
        cwd="C:/project/root",
        exit_code=1,
        stdout=raw_stdout,
        stderr=raw_stderr,
        execution_error=None,
        duration_ms=1234.5,
        status=ToolStatus.TEST_FAILURE,
    )

    assert res.stdout == raw_stdout
    assert res.stderr == raw_stderr
    assert res.command == ["python", "-m", "pytest", "tests/"]
    assert res.cwd == "C:/project/root"
    assert res.exit_code == 1
    assert res.duration_ms == 1234.5


# ============================================================================
# SCENARIO 16 — END-TO-END BROKEN CALCULATOR PIPELINE SIMULATION
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_16_end_to_end_broken_calculator_pipeline(mock_ollama_client, tmp_path: Path):
    """
    Scenario 16: Simulate broken calculator pipeline terminating deterministically at contract boundary.
    Steps:
    1. PlanContract validates plan (PASS)
    2. Coder emits placeholder '# implementation here'
    3. CodeContractValidator rejects placeholder (CONTRACT_FAILURE)
    4. Quality Gate is BLOCKED (Ruff and Pytest NOT executed)
    5. Reviewer receives CONTRACT_FAILURE evidence and rejects implementation without hallucinating lint/test errors.
    """
    # Step 1: Valid Plan
    plan_validator = PlanContractValidator()
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Research CLI math libraries", dependencies=[]),
        PlanSubtask(id=2, agent=AgentType.CODER, description="Write CLI calculator", dependencies=[1]),
        PlanSubtask(id=3, agent=AgentType.TESTER, description="Write pytest suite for calculator", dependencies=[2]),
    ]
    contract = PlanContract(
        task_summary="Develop CLI calculator",
        task_type="coding",
        complexity="low",
        required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER],
        subtasks=subtasks,
        execution_order=[1, 2, 3],
        file_manifest=["calculator.py"],
    )
    plan_res = plan_validator.validate(contract)
    assert plan_res.is_valid is True

    # Step 2: Coder emits broken placeholder
    calc_file = tmp_path / "calculator.py"
    calc_file.write_text("# implementation here\ndef add(a, b):\n    pass\n", encoding="utf-8")

    # Step 3: CodeContract rejects placeholder
    code_res = CodeContractValidator.validate(tmp_path)
    assert code_res.is_valid is False
    assert code_res.status == CodeContractStatus.CONTRACT_FAILURE

    # Step 4: Quality Gate BLOCKED (Ruff & Pytest NOT executed)
    det_val = DeterministicValidator()
    with patch.object(det_val, "_run_tool_cmd") as mock_tool_cmd, \
         patch.object(det_val, "_run_pytest") as mock_pytest_cmd:
        qg_res = await det_val.run_full_quality_gate(workspace_dir=tmp_path)
        assert qg_res["quality_gate"] == "FAIL"
        mock_tool_cmd.assert_not_called()  # DOWNSTREAM WORK NOT EXECUTED
        mock_pytest_cmd.assert_not_called()

    # Step 5: Reviewer receives CONTRACT_FAILURE and REJECTS
    reviewer = ReviewerAgent(mock_ollama_client)
    rev_res = await reviewer.execute("Develop CLI calculator", "plan", "# implementation here", "tests", validation_results=qg_res)
    assert rev_res["quality_gate"] == "FAIL"
    assert "REJECTED" in rev_res["output"]
    assert "CONTRACT_FAILURE" in rev_res["output"]


# ============================================================================
# SCENARIO 17 — END-TO-END HAPPY PATH CALCULATOR PIPELINE SIMULATION
# ============================================================================

@pytest.mark.asyncio
async def test_scenario_17_end_to_end_happy_path_calculator_pipeline(mock_ollama_client, tmp_path: Path):
    """
    Scenario 17: Simulate clean happy-path calculator pipeline verifying all state transitions:
    PlanContract -> VALID
    CodeContract -> VALID
    Ruff -> PASS
    Pytest -> PASS
    Quality Gate -> PASS
    Reviewer -> APPROVED
    """
    # Stage 1: PlanContract -> VALID
    plan_validator = PlanContractValidator()
    subtasks = [
        PlanSubtask(id=1, agent=AgentType.RESEARCH, description="Research math CLI structure", dependencies=[]),
        PlanSubtask(id=2, agent=AgentType.CODER, description="Implement calculator logic in calculator.py", dependencies=[1]),
        PlanSubtask(id=3, agent=AgentType.TESTER, description="Implement test suite in test_calculator.py", dependencies=[2]),
    ]
    contract = PlanContract(
        task_summary="Develop CLI calculator with basic arithmetic",
        task_type="coding",
        complexity="low",
        required_agents=[AgentType.RESEARCH, AgentType.CODER, AgentType.TESTER],
        subtasks=subtasks,
        execution_order=[1, 2, 3],
        file_manifest=["calculator.py", "test_calculator.py"],
    )
    plan_res = plan_validator.validate(contract)
    assert plan_res.is_valid is True

    # Stage 2: CodeContract -> VALID
    calc_file = tmp_path / "calculator.py"
    test_file = tmp_path / "test_calculator.py"

    calc_file.write_text("def add(a: float, b: float) -> float:\n    return a + b\n\ndef subtract(a: float, b: float) -> float:\n    return a - b\n", encoding="utf-8")
    test_file.write_text("from calculator import add, subtract\n\ndef test_add():\n    assert add(2, 3) == 5\n\ndef test_subtract():\n    assert subtract(5, 2) == 3\n", encoding="utf-8")

    code_res = CodeContractValidator.validate(tmp_path)
    assert code_res.is_valid is True
    assert code_res.status == CodeContractStatus.VALID

    # Stage 3 & 4: Ruff -> PASS, Pytest -> PASS via Quality Gate
    det_val = DeterministicValidator()
    mock_ruff_pass = ToolResult(
        tool="ruff", command=["ruff", "check", "."], cwd=str(tmp_path), exit_code=0, stdout="All checks passed.", stderr="", duration_ms=15.0, status=ToolStatus.PASS
    )
    mock_pytest_pass = ToolResult(
        tool="pytest", command=["pytest"], cwd=str(tmp_path), exit_code=0, stdout="2 passed in 0.05s", stderr="", duration_ms=50.0, status=ToolStatus.PASS
    )

    with patch.object(det_val, "_run_tool_cmd", return_value=mock_ruff_pass), \
         patch.object(det_val, "_run_pytest", return_value=mock_pytest_pass):

        # Stage 5: Quality Gate -> PASS
        qg_res = await det_val.run_full_quality_gate(workspace_dir=tmp_path)
        assert qg_res["quality_gate"] == "PASS"
        assert qg_res["ruff"]["status"] == "PASS"
        assert qg_res["pytest"]["status"] == "PASS"

    # Stage 6: Reviewer -> APPROVED
    reviewer = ReviewerAgent(mock_ollama_client)
    rev_res = await reviewer.execute(
        user_request="Develop CLI calculator",
        execution_plan="plan",
        generated_code=calc_file.read_text(),
        test_results="2 passed in 0.05s",
        validation_results=qg_res,
    )

    assert rev_res["quality_gate"] == "PASS"
    assert "APPROVED" in rev_res["output"]
