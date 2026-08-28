import os
import sys
import pytest
from pathlib import Path
from app.utils.sandbox import SecureExecutor


@pytest.mark.asyncio(loop_scope="module")
async def test_sandbox_normal_execution():
    """Verify that normal Python code executes and returns exit code 0."""
    executor = SecureExecutor(timeout=5.0)
    cwd = Path("sandbox_workspace")
    cwd.mkdir(exist_ok=True)
    
    # Write a simple script
    script_path = cwd / "test_normal.py"
    script_path.write_text("print('Hello from sandbox!')\n", encoding="utf-8")
    
    # Use absolute path to avoid cwd mismatch
    cmd = [sys.executable, str(script_path.resolve())]
    result = await executor.execute_command(cmd, cwd)
    
    assert result["passed"] is True
    assert result["exit_code"] == 0
    assert "Hello from sandbox!" in result["stdout"]
    assert result["timeout_triggered"] is False
    
    # Clean up
    if script_path.exists():
        script_path.unlink()


@pytest.mark.asyncio(loop_scope="module")
async def test_sandbox_timeout_execution():
    """Verify that an infinite loop gets terminated by the timeout."""
    # Use a small timeout of 1.0 seconds so tests run quickly
    executor = SecureExecutor(timeout=1.0)
    cwd = Path("sandbox_workspace")
    cwd.mkdir(exist_ok=True)
    
    script_path = cwd / "test_timeout.py"
    script_path.write_text("import time\nwhile True:\n    time.sleep(0.1)\n", encoding="utf-8")
    
    # Use absolute path to avoid cwd mismatch
    cmd = [sys.executable, str(script_path.resolve())]
    result = await executor.execute_command(cmd, cwd)
    
    assert result["passed"] is False
    assert result["exit_code"] == -1
    assert result["timeout_triggered"] is True
    
    # Clean up
    if script_path.exists():
        script_path.unlink()


@pytest.mark.asyncio(loop_scope="module")
async def test_sandbox_environment_isolation():
    """Verify that sensitive environment variables do not leak into the sandbox."""
    # Temporarily set a dummy sensitive variable on the host environment
    os.environ["GROQ_API_KEY"] = "gsk_test_api_key_value_12345"
    
    executor = SecureExecutor(timeout=5.0)
    cwd = Path("sandbox_workspace")
    cwd.mkdir(exist_ok=True)
    
    script_path = cwd / "test_env.py"
    script_path.write_text(
        "import os\n"
        "print('GROQ_API_KEY:', os.environ.get('GROQ_API_KEY'))\n"
        "print('SECRET:', os.environ.get('JWT_SECRET_KEY'))\n",
        encoding="utf-8"
    )
    
    # Use absolute path to avoid cwd mismatch
    cmd = [sys.executable, str(script_path.resolve())]
    result = await executor.execute_command(cmd, cwd)
    
    assert result["passed"] is True
    assert "GROQ_API_KEY: None" in result["stdout"]
    assert "SECRET: None" in result["stdout"]
    
    # Clean up
    if script_path.exists():
        script_path.unlink()
    # Clean up host env
    os.environ.pop("GROQ_API_KEY", None)
