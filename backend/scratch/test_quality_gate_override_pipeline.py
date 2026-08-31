"""
End-to-End Validation Script for Quality Gate Enforcement & Reviewer Evidence.
Tests both:
  1. Broken implementation -> Ruff FAIL, Pytest FAIL, Quality Gate FAIL, Reviewer REJECTED.
  2. Correct implementation -> Ruff PASS, Pytest PASS, Quality Gate PASS, Reviewer APPROVED.
"""

import asyncio
import uuid
import sys
import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath("."))

from app.agents.reviewer import ReviewerAgent
from app.agents.validator import DeterministicValidator
from app.ai.ollama_client import OllamaClient
from app.services.workspace_service import WorkspaceService, SANDBOX_DIR
from app.db.database import init_db, async_session_factory


async def main():
    print("=== STARTING DETERMINISTIC QUALITY GATE VALIDATION SUITE ===")
    client = OllamaClient()
    reviewer = ReviewerAgent(client)
    validator = DeterministicValidator()

    await init_db()
    async with async_session_factory() as db:
        # TEST CASE 1: BROKEN IMPLEMENTATION (Syntax error / Undefined name)
        print("\n--- TEST CASE 1: BROKEN IMPLEMENTATION ---")
        session_id_broken = uuid.uuid4()
        ws_broken = WorkspaceService(db, session_id_broken)
    
    # Write broken python file with missing import (F821 Undefined name TaskStatus)
    broken_code = (
        "class Task:\n"
        "    status: TaskStatus = TaskStatus.pending\n"
    )
    await ws_broken.write_file("main.py", broken_code, "python")
    print(f"Created broken file in workspace: {ws_broken.workspace_dir}")

    # Run deterministic validator
    val_res = await validator.validate(ws_broken.workspace_dir)
    print(f"Validator result on broken code: passed={val_res['passed']}")
    assert val_res["passed"] is False, "Validator MUST fail on broken code!"

    # Run ReviewerAgent on broken implementation
    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        # Simulate LLM outputting false optimism
        mock_chat.return_value = (
            "### Review Summary:\n"
            "Looks good!\n"
            "Correctness: PASS\n"
            "Quality Score: 85/100\n"
            "Final Status: APPROVED_WITH_WARNINGS"
        )
        rev_res = await reviewer.execute(
            user_request="Build task app",
            execution_plan="Plan",
            generated_code=broken_code,
            test_results="DETERMINISTIC VALIDATION FAILED:\nF821 Undefined name TaskStatus",
            test_passed=False,
            session_id=str(session_id_broken)
        )

    print(f"Reviewer Quality Gate: {rev_res['quality_gate']}")
    print(f"Reviewer Score: {rev_res['overall_score']}")

    assert rev_res["quality_gate"] == "FAIL", "Reviewer Quality Gate MUST be FAIL!"
    assert rev_res["overall_score"] <= 40.0, "Overall score MUST be capped at 40.0 on failure!"
    assert "Final Quality Gate: FAIL (REJECTED)" in rev_res["output"]
    print("[PASS] Test Case 1 PASSED: Broken implementation correctly marked as FAIL / REJECTED!")

    # TEST CASE 2: CORRECT IMPLEMENTATION
    print("\n--- TEST CASE 2: CORRECT IMPLEMENTATION ---")
    session_id_clean = uuid.uuid4()
    ws_clean = WorkspaceService(db, session_id_clean)

    clean_code = (
        "from enum import Enum\n\n"
        "class TaskStatus(str, Enum):\n"
        "    pending = 'pending'\n\n"
        "class Task:\n"
        "    status: TaskStatus = TaskStatus.pending\n\n"
    )
    await ws_clean.write_file("main.py", clean_code, "python")
    print(f"Created clean file in workspace: {ws_clean.workspace_dir}")

    # Run deterministic validator
    val_res_clean = await validator.validate(ws_clean.workspace_dir)
    print(f"Validator result on clean code: passed={val_res_clean['passed']}")
    assert val_res_clean["passed"] is True, "Validator MUST pass on clean code!"

    # Run ReviewerAgent on clean implementation
    with patch.object(client, "chat", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = (
            "### Review Summary:\n"
            "Implementation is clean and well-structured.\n"
            "Correctness: PASS\n"
            "Quality Score: 95/100\n"
            "Final Status: APPROVED"
        )
        rev_res_clean = await reviewer.execute(
            user_request="Build task app",
            execution_plan="Plan",
            generated_code=clean_code,
            test_results="All 5 pytest unit tests passed cleanly.",
            test_passed=True,
            session_id=str(session_id_clean)
        )

    print(f"Reviewer Quality Gate: {rev_res_clean['quality_gate']}")
    print(f"Reviewer Score: {rev_res_clean['overall_score']}")
    print(f"Lint findings: {rev_res_clean['lint_findings']}")

    assert rev_res_clean["quality_gate"] in ("PASS", "PASS_WITH_WARNINGS"), "Reviewer Quality Gate MUST be PASS or PASS_WITH_WARNINGS!"
    assert rev_res_clean["overall_score"] == 95.0, "Overall score should match clean LLM assessment!"
    assert "Final Quality Gate:" in rev_res_clean["output"]
    print("[PASS] Test Case 2 PASSED: Clean implementation correctly marked as PASS / APPROVED!")

    print("\n=== ALL DETERMINISTIC QUALITY GATE TESTS PASSED PERFECTLY ===")


if __name__ == "__main__":
    asyncio.run(main())
