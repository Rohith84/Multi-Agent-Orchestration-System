"""
Tests for Phase 3: Deterministic Graph Contract Validator.

Validates that:
- Linear and custom DAG workflows pass GraphContract validation.
- Empty graphs, duplicate IDs, missing/empty IDs, invalid types are rejected.
- Non-existent edge endpoints, duplicate edges, self-loops, directed cycles, unreachable nodes,
  and excessive node counts (>20) are rejected deterministically.
- DynamicGraphCompiler rejects invalid graphs before StateGraph node/edge construction.
"""

import pytest
from pydantic import ValidationError

from app.schemas.contracts import GraphContract, GraphNode, GraphEdge, GraphNodeType
from app.orchestration.graph_validator import (
    GraphContractValidator,
    GraphContractValidationError,
)
from app.orchestration.dynamic_graph import DynamicGraphCompiler


def test_1_valid_linear_graph():
    """1. Valid linear graph: planner -> research -> coder -> tester -> reviewer."""
    graph_json = {
        "nodes": [
            {"id": "node_planner", "type": "planner"},
            {"id": "node_research", "type": "research"},
            {"id": "node_coder", "type": "coder"},
            {"id": "node_tester", "type": "tester"},
            {"id": "node_reviewer", "type": "reviewer"},
        ],
        "edges": [
            {"source": "node_planner", "target": "node_research"},
            {"source": "node_research", "target": "node_coder"},
            {"source": "node_coder", "target": "node_tester"},
            {"source": "node_tester", "target": "node_reviewer"},
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is True
    assert res.contract is not None
    assert len(res.contract.nodes) == 5
    assert len(res.contract.edges) == 4


def test_2_empty_graph_rejected():
    """2. Empty graph is rejected."""
    graph_json = {"nodes": [], "edges": []}
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("at least 1 node" in err for err in res.errors)


def test_3_duplicate_node_ids_rejected():
    """3. Duplicate node IDs are rejected."""
    graph_json = {
        "nodes": [
            {"id": "step_1", "type": "planner"},
            {"id": "step_1", "type": "coder"},  # Duplicate ID
        ],
        "edges": [],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("Duplicate node ID 'step_1'" in err for err in res.errors)


def test_4_missing_node_id_rejected():
    """4. Missing node ID is rejected."""
    graph_json = {
        "nodes": [
            {"type": "planner"},  # Missing 'id'
        ],
        "edges": [],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert len(res.errors) > 0


def test_5_empty_node_id_rejected():
    """5. Empty node ID is rejected."""
    graph_json = {
        "nodes": [
            {"id": "   ", "type": "planner"},  # Whitespace/empty ID
        ],
        "edges": [],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("Node ID cannot be empty" in err for err in res.errors)


def test_6_invalid_node_type_rejected():
    """6. Invalid built-in node type is rejected."""
    graph_json = {
        "nodes": [
            {"id": "node_1", "type": "unauthorized_arbitrary_daemon"},
        ],
        "edges": [],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert len(res.errors) > 0


def test_7_missing_edge_source_rejected():
    """7. Missing edge source is rejected."""
    graph_json = {
        "nodes": [
            {"id": "n1", "type": "planner"},
            {"id": "n2", "type": "coder"},
        ],
        "edges": [
            {"target": "n2"},  # Missing 'source'
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert len(res.errors) > 0


def test_8_missing_edge_target_rejected():
    """8. Missing edge target is rejected."""
    graph_json = {
        "nodes": [
            {"id": "n1", "type": "planner"},
            {"id": "n2", "type": "coder"},
        ],
        "edges": [
            {"source": "n1"},  # Missing 'target'
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert len(res.errors) > 0


def test_9_edge_referencing_nonexistent_source_rejected():
    """9. Edge referencing non-existent source is rejected."""
    graph_json = {
        "nodes": [
            {"id": "n1", "type": "planner"},
            {"id": "n2", "type": "coder"},
        ],
        "edges": [
            {"source": "ghost_node", "target": "n2"},
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("non-existent source node 'ghost_node'" in err for err in res.errors)


def test_10_edge_referencing_nonexistent_target_rejected():
    """10. Edge referencing non-existent target is rejected."""
    graph_json = {
        "nodes": [
            {"id": "n1", "type": "planner"},
            {"id": "n2", "type": "coder"},
        ],
        "edges": [
            {"source": "n1", "target": "phantom_node"},
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("non-existent target node 'phantom_node'" in err for err in res.errors)


def test_11_duplicate_edge_rejected():
    """11. Duplicate edge is rejected."""
    graph_json = {
        "nodes": [
            {"id": "n1", "type": "planner"},
            {"id": "n2", "type": "coder"},
        ],
        "edges": [
            {"source": "n1", "target": "n2"},
            {"source": "n1", "target": "n2"},  # Duplicate edge
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("Duplicate edge from 'n1' to 'n2'" in err for err in res.errors)


def test_12_cycle_rejected():
    """12. Directed cycle (A -> B -> A) is detected and rejected."""
    graph_json = {
        "nodes": [
            {"id": "node_a", "type": "planner"},
            {"id": "node_b", "type": "coder"},
        ],
        "edges": [
            {"source": "node_a", "target": "node_b"},
            {"source": "node_b", "target": "node_a"},  # Cycle!
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("Directed cycle detected" in err for err in res.errors)


def test_13_unreachable_node_rejected():
    """13. Unreachable node is detected and rejected."""
    graph_json = {
        "nodes": [
            {"id": "start_node", "type": "planner"},
            {"id": "coder_node", "type": "coder"},
            {"id": "isolated_node", "type": "tester"},  # Not reachable from start_node
        ],
        "edges": [
            {"source": "start_node", "target": "coder_node"},
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("Unreachable node(s) detected: ['isolated_node']" in err for err in res.errors)


def test_14_excessive_graph_size_rejected():
    """14. Excessive graph size (>20 nodes) is rejected."""
    nodes = [{"id": f"node_{i}", "type": "coder"} for i in range(1, 25)]
    graph_json = {"nodes": nodes, "edges": []}
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is False
    assert any("Maximum 20 nodes allowed" in err for err in res.errors)


def test_15_valid_custom_node():
    """15. Valid custom/fallback node is accepted."""
    graph_json = {
        "nodes": [
            {"id": "plan_node", "type": "planner"},
            {"id": "custom_agent", "type": "custom", "config": {"system_prompt": "You are a specialist."}},
            {"id": "review_node", "type": "reviewer"},
        ],
        "edges": [
            {"source": "plan_node", "target": "custom_agent"},
            {"source": "custom_agent", "target": "review_node"},
        ],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is True
    assert res.contract is not None
    assert res.contract.nodes[1].type == GraphNodeType.CUSTOM


def test_16_valid_linear_fallback_without_edges():
    """16. Valid graph with linear fallback when edges are absent."""
    graph_json = {
        "nodes": [
            {"id": "p", "type": "planner"},
            {"id": "r", "type": "research"},
            {"id": "c", "type": "coder"},
        ],
        "edges": [],
    }
    res = GraphContractValidator.validate(graph_json)
    assert res.is_valid is True
    assert len(res.contract.nodes) == 3
    assert len(res.contract.edges) == 0


def test_17_compiler_rejects_invalid_graph_before_compilation():
    """17. DynamicGraphCompiler rejects invalid graph JSON before StateGraph compilation."""
    invalid_graph_json = {
        "nodes": [
            {"id": "n1", "type": "planner"},
            {"id": "n2", "type": "coder"},
        ],
        "edges": [
            {"source": "n1", "target": "non_existent_target"},
        ],
    }
    compiler = DynamicGraphCompiler()
    with pytest.raises(GraphContractValidationError) as exc_info:
        compiler.compile(invalid_graph_json)

    assert "Graph Contract Violation" in str(exc_info.value)
    assert "non-existent target node 'non_existent_target'" in str(exc_info.value)
