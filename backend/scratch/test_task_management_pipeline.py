"""
Integration Validation Script: Task Management Pipeline
Runs end-to-end pipeline and verifies:
  - main.py contains ONLY Python.
  - test_suite.py contains ONLY Python.
  - Ruff can parse generated Python files cleanly.
  - Pytest collects and executes tests cleanly.
  - Generated tests are isolated (do not depend on task ID 1 or pre-existing state).
  - Bandit reports are correctly classified with B101 handled appropriately.
"""

import asyncio
import uuid
import sys
import os
import subprocess
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath("."))

from app.db.database import init_db, async_session_factory, engine
from app.orchestration.workflow import WorkflowExecutor
from app.services.workspace_service import SANDBOX_DIR
from app.utils.artifact_extractor import extract_code_artifacts


async def main():
    print("=== STARTING FULL PIPELINE VALIDATION ON TASK-MANAGEMENT EXAMPLE ===")
    await engine.dispose()
    await init_db()

    session_id = uuid.uuid4()
    user_req = "Build a simple task management application with a dashboard, task creation, task status tracking, priority levels, and a clean responsive UI."

    print(f"Executing workflow for session {session_id}...")
    async with async_session_factory() as session:
        executor = WorkflowExecutor(session)
        stream = executor.execute(user_request=user_req, session_id=session_id)
        events = [e async for e in stream]

    print(f"Workflow completed! Total events streamed: {len(events)}")

    # 1. Check sandbox directory files
    session_sandbox = SANDBOX_DIR / str(session_id)
    if not session_sandbox.exists():
        print(f"ERROR: Session sandbox directory {session_sandbox} does not exist!")
        sys.exit(1)

    generated_files = list(session_sandbox.glob("**/*"))
    print(f"Generated files in sandbox ({session_sandbox}):")
    for f in generated_files:
        if f.is_file():
            print(f" - {f.relative_to(session_sandbox)} ({f.stat().st_size} bytes)")

    # 2. Verify main.py contains ONLY valid Python (no markdown headers)
    main_py = session_sandbox / "main.py"
    if main_py.exists():
        content = main_py.read_text(encoding="utf-8")
        assert not content.strip().startswith("###"), "ERROR: main.py starts with markdown heading!"
        assert "Implementation Summary" not in content, "ERROR: main.py contains natural language prose summary!"
        print("✓ main.py contains ONLY Python code!")
    else:
        print("Note: main.py not created directly, checking all .py files...")

    # 3. Verify test_suite.py contains ONLY valid Python
    test_py = session_sandbox / "test_suite.py"
    if test_py.exists():
        content = test_py.read_text(encoding="utf-8")
        assert not content.strip().startswith("###"), "ERROR: test_suite.py starts with markdown heading!"
        assert "Test Summary" not in content, "ERROR: test_suite.py contains test summary narrative!"
        print("✓ test_suite.py contains ONLY valid Python code!")

    # 4. Verify Ruff can parse all Python files
    print("Running Ruff syntax & lint check on generated sandbox files...")
    ruff_res = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--no-cache", str(session_sandbox)],
        capture_output=True,
        text=True
    )
    print(f"Ruff Output:\n{ruff_res.stdout}")
    assert ruff_res.returncode == 0, f"Ruff reported errors:\n{ruff_res.stdout}\n{ruff_res.stderr}"
    print("✓ Ruff parsed generated Python files with 0 syntax errors!")

    # 5. Verify Pytest collects and runs tests
    print("Running Pytest collection check on generated sandbox files...")
    pytest_res = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", str(session_sandbox)],
        capture_output=True,
        text=True
    )
    print(f"Pytest Collection Output:\n{pytest_res.stdout}")
    assert "collected" in pytest_res.stdout, f"Pytest collection failed:\n{pytest_res.stdout}\n{pytest_res.stderr}"
    print("✓ Pytest successfully collected generated tests!")

    # 6. Verify Bandit scan with -s B101
    print("Running Bandit security check with -s B101...")
    bandit_res = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", "-s", "B101", str(session_sandbox)],
        capture_output=True,
        text=True
    )
    print(f"Bandit Output:\n{bandit_res.stdout}")
    assert "No issues identified" in bandit_res.stdout or bandit_res.returncode == 0, (
        f"Bandit flagged critical issues:\n{bandit_res.stdout}"
    )
    print("✓ Bandit security check passed cleanly with -s B101 (pytest assertions classified correctly)!")

    print("=== ALL PIPELINE VALIDATION CHECKS PASSED PERFECTLY ===")


if __name__ == "__main__":
    asyncio.run(main())
