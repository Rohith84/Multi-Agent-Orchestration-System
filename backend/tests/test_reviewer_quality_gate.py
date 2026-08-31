"""
Unit tests for Reviewer Agent Authoritative Deterministic Quality Gate Enforcement.
Verifies that:
  1. Ruff or Pytest failures force Quality Gate = FAIL and score cap at 40/100.
  2. LLM text output cannot override deterministic failure evidence.
  3. Genuine clean implementations receive Quality Gate = PASS / APPROVED.
  4. Missing validation_results fails closed (Quality Gate = FAIL).
"""

import pytest
import uuid
from unittest.mock import AsyncMock, patch
from app.agents.reviewer import ReviewerAgent
from app.ai.ollama_client import OllamaClient


@pytest.mark.asyncio
async def test_reviewer_deterministic_failure_override_prevention():
    """
    Verify that when Quality Gate reports a failure, ReviewerAgent forces Quality Gate = FAIL,
    caps overall score at <= 40.0, and marks the result as REJECTED even if the LLM outputted APPROVED.
    """
    client = OllamaClient()
    agent = ReviewerAgent(client)

    # Hallucinating LLM response that claims code is approved
    hallucinated_llm_response = (
        "### Review Summary:\n"
        "The implementation looks great!\n"
        "Correctness: PASS\n"
        "Architecture: PASS\n"
        "Test Result Assessment: PASS\n"
        "Quality Score: 85/100\n"
        "Final Status: APPROVED_WITH_WARNINGS"
    )

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = hallucinated_llm_response

        # Pre-computed validation_results from Quality Gate showing FAIL
        validation_results = {
            "deterministic_checks": {"status": "PASS", "output": "All checks passed"},
            "ruff": {"status": "FAIL", "output": "main.py:6:26: F821 Undefined name `TaskStatus`"},
            "pytest": {"status": "FAIL", "output": "DETERMINISTIC VALIDATION FAILED:\nSyntaxError in main.py"},
            "bandit": {"status": "PASS", "output": "No issues identified."},
            "quality_gate": "FAIL",
            "test_passed": False,
        }

        result = await agent.execute(
            user_request="Build task app",
            execution_plan="Plan",
            generated_code="def task(): pass",
            test_results="DETERMINISTIC VALIDATION FAILED:\nSyntaxError in main.py",
            validation_results=validation_results,
            session_id=str(uuid.uuid4())
        )

        # Assertions
        assert result["quality_gate"] == "FAIL", "Quality Gate MUST be FAIL when linter/pytest failed!"
        assert result["overall_score"] <= 40.0, f"Score MUST be capped at 40.0 on failure, got {result['overall_score']}"
        assert "Final Quality Gate: FAIL (REJECTED)" in result["output"]
        assert "Ruff Status: FAIL" in result["output"]
        assert "Pytest Status: FAIL" in result["output"]
        mock_chat.assert_not_awaited()


@pytest.mark.asyncio
async def test_reviewer_clean_implementation_approved():
    """
    Verify that when Quality Gate reports all tools pass cleanly, Quality Gate = PASS.
    """
    client = OllamaClient()
    agent = ReviewerAgent(client)

    clean_llm_response = (
        "### Review Summary:\n"
        "Code is well-structured and passes all tests.\n"
        "Correctness: PASS\n"
        "Architecture: PASS\n"
        "Quality Score: 92/100\n"
        "Final Status: APPROVED"
    )

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = clean_llm_response

        # Pre-computed validation_results from Quality Gate showing PASS
        validation_results = {
            "deterministic_checks": {"status": "PASS", "output": "All checks passed"},
            "ruff": {"status": "PASS", "output": "Passed cleanly."},
            "pytest": {"status": "PASS", "output": "5 passed in 1.2s"},
            "bandit": {"status": "PASS", "output": "No issues identified."},
            "quality_gate": "PASS",
            "test_passed": True,
        }

        result = await agent.execute(
            user_request="Build task app",
            execution_plan="Plan",
            generated_code="def task(): pass",
            test_results="All 5 pytest unit tests passed cleanly.",
            validation_results=validation_results,
            session_id=str(uuid.uuid4())
        )

        assert result["quality_gate"] == "PASS"
        assert result["overall_score"] == 92.0
        assert "Final Quality Gate: PASS (APPROVED)" in result["output"]


@pytest.mark.asyncio
async def test_reviewer_missing_validation_results_fails_closed():
    """
    Verify that when no validation_results are provided, Reviewer fails closed (FAIL, not PASS).
    """
    client = OllamaClient()
    agent = ReviewerAgent(client)

    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = "Quality Score: 95/100\nFinal Status: APPROVED"

        result = await agent.execute(
            user_request="Build task app",
            execution_plan="Plan",
            generated_code="def task(): pass",
            test_results="",
            validation_results=None,  # No validation_results!
            session_id=str(uuid.uuid4())
        )

        # Must fail closed
        assert result["quality_gate"] == "FAIL", "Missing validation_results must result in FAIL, not PASS"
        assert result["overall_score"] <= 40.0, f"Score must be capped when failing closed, got {result['overall_score']}"
        assert "REJECTED" in result["output"]
