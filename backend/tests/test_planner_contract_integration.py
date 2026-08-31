"""
Tests for Phase 2: Planner Agent & Plan Contract Integration.

Validates that:
- PlannerAgent processes mocked LLM JSON responses deterministically.
- Valid plans return is_valid=True with a verified PlanContract.
- Malformed JSON, missing fields, invalid agents, broken dependencies, and 577-step outputs
  are rejected deterministically without executing downstream.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.agents.planner import PlannerAgent, PlannerResult
from app.ai.ollama_client import OllamaClient
from app.schemas.contracts import AgentType


@pytest.fixture
def mock_ollama_client():
    client = MagicMock(spec=OllamaClient)
    client.chat = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_valid_planner_response(mock_ollama_client):
    """Verify that a valid JSON plan from LLM is validated into a PlanContract."""
    valid_json_plan = {
        "task_summary": "Build CLI Calculator",
        "task_type": "coding",
        "complexity": "low",
        "required_agents": ["research", "coder", "tester", "reviewer"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research arithmetic CLI requirements", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Implement calculator operations in calculator.py", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Write pytest test suite in test_calculator.py", "dependencies": [2]},
            {"id": 4, "agent": "reviewer", "description": "Perform quality gate review and validation", "dependencies": [3]},
        ],
        "file_manifest": ["calculator.py", "test_calculator.py"],
        "acceptance_criteria": ["All tests pass", "No lint errors"],
    }
    mock_ollama_client.chat.return_value = f"```json\n{json.dumps(valid_json_plan)}\n```"

    planner = PlannerAgent(mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Build a CLI calculator")

    assert res.is_valid is True
    assert res.contract is not None
    assert len(res.contract.subtasks) == 4
    assert res.contract.task_summary == "Build CLI Calculator"
    assert "### Task Summary: Build CLI Calculator" in res.formatted_plan


@pytest.mark.asyncio
async def test_malformed_json_rejected(mock_ollama_client):
    """Verify that malformed/unparseable JSON is rejected deterministically."""
    mock_ollama_client.chat.return_value = '```json\n{"task_summary": "Broken plan", "subtasks": [ INVALID JSON HERE\n```'

    planner = PlannerAgent(mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Build a CLI calculator")

    assert res.is_valid is False
    assert res.contract is None
    assert len(res.errors) > 0
    assert "Plan Validation Error" in res.formatted_plan


@pytest.mark.asyncio
async def test_577_subtasks_rejected(mock_ollama_client):
    """Verify that a 577-subtask runaway LLM output is rejected deterministically."""
    subtasks = [
        {"id": i, "agent": "coder", "description": f"Coder step {i}", "dependencies": []}
        for i in range(1, 578)
    ]
    runaway_json = {
        "task_summary": "Runaway plan",
        "task_type": "coding",
        "required_agents": ["coder"],
        "subtasks": subtasks,
    }
    mock_ollama_client.chat.return_value = json.dumps(runaway_json)

    planner = PlannerAgent(mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Runaway request")

    assert res.is_valid is False
    assert res.contract is None
    assert any("Maximum 6 subtasks allowed" in err for err in res.errors)


@pytest.mark.asyncio
async def test_missing_required_fields_rejected(mock_ollama_client):
    """Verify that a plan missing required fields (e.g. task_summary or subtasks) is rejected."""
    incomplete_json = {
        "task_type": "coding",
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research specs", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Write code", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Run tests", "dependencies": [2]},
        ]
        # Missing task_summary and required_agents
    }
    mock_ollama_client.chat.return_value = json.dumps(incomplete_json)

    planner = PlannerAgent(mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Incomplete request")

    assert res.is_valid is False
    assert res.contract is None
    assert len(res.errors) > 0


@pytest.mark.asyncio
async def test_invalid_agent_in_planner_output_rejected(mock_ollama_client):
    """Verify that an unauthorized agent in subtasks is rejected."""
    invalid_agent_json = {
        "task_summary": "Unauthorized agent plan",
        "task_type": "coding",
        "required_agents": ["research", "coder", "tester"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research specs", "dependencies": []},
            {"id": 2, "agent": "unauthorized_hacker", "description": "Write code", "dependencies": [1]},
            {"id": 3, "agent": "tester", "description": "Run tests", "dependencies": [2]},
        ],
    }
    mock_ollama_client.chat.return_value = json.dumps(invalid_agent_json)

    planner = PlannerAgent(mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Invalid agent request")

    assert res.is_valid is False
    assert res.contract is None
    assert len(res.errors) > 0


@pytest.mark.asyncio
async def test_invalid_dependencies_in_planner_output_rejected(mock_ollama_client):
    """Verify that a subtask referencing a non-existent dependency ID is rejected."""
    broken_dep_json = {
        "task_summary": "Broken dependency plan",
        "task_type": "coding",
        "required_agents": ["research", "coder", "tester"],
        "subtasks": [
            {"id": 1, "agent": "research", "description": "Research specs", "dependencies": []},
            {"id": 2, "agent": "coder", "description": "Write code", "dependencies": [999]},  # Non-existent 999
            {"id": 3, "agent": "tester", "description": "Run tests", "dependencies": [2]},
        ],
    }
    mock_ollama_client.chat.return_value = json.dumps(broken_dep_json)

    planner = PlannerAgent(mock_ollama_client)
    res: PlannerResult = await planner.execute_contract("Broken dependency request")

    assert res.is_valid is False
    assert res.contract is None
    assert any("references non-existent dependency '999'" in err for err in res.errors)
