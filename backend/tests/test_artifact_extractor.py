"""
Unit tests for the Artifact Extractor utility.
Verifies that natural language prose is filtered out and ONLY clean source code artifacts are extracted.
"""

import pytest
from app.utils.artifact_extractor import extract_code_artifacts, CodeArtifact, is_valid_filename


def test_is_valid_filename():
    assert is_valid_filename("main.py") is True
    assert is_valid_filename("app/routes/tasks.py") is True
    assert is_valid_filename("Dockerfile") is True
    assert is_valid_filename("docker-compose.yml") is True
    assert is_valid_filename("requirements.txt") is True
    assert is_valid_filename("config.json") is True
    
    assert is_valid_filename("") is False
    assert is_valid_filename("<invalid>:path.py") is False


def test_extracts_clean_code_excluding_surrounding_prose():
    llm_output = (
        "### Implementation Summary:\n"
        "The implementation involves setting up a task management service with FastAPI.\n\n"
        "```python\n"
        "# main.py\n"
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "@app.get('/tasks')\n"
        "def get_tasks():\n"
        "    return [{'id': 1, 'title': 'Test Task'}]\n"
        "```\n\n"
        "### Next Steps:\n"
        "Run uvicorn main:app to start the server."
    )

    artifacts = extract_code_artifacts(llm_output)
    assert len(artifacts) == 1
    art = artifacts[0]
    assert art.path == "main.py"
    assert "### Implementation Summary:" not in art.content
    assert "### Next Steps:" not in art.content
    assert "from fastapi import FastAPI" in art.content
    assert art.content.startswith("from fastapi import FastAPI")


def test_extracts_multiple_annotated_files():
    llm_output = (
        "Here are the implementation files:\n\n"
        "```python filepath=\"app/models/task.py\"\n"
        "class Task:\n"
        "    id: int\n"
        "```\n\n"
        "```yaml filepath=\"docker-compose.yml\"\n"
        "version: '3.8'\n"
        "services:\n"
        "  web:\n"
        "    image: app:latest\n"
        "```\n\n"
        "```dockerfile filepath=\"Dockerfile\"\n"
        "FROM python:3.11\n"
        "WORKDIR /app\n"
        "```\n"
    )

    artifacts = extract_code_artifacts(llm_output)
    assert len(artifacts) == 3

    paths = {a.path: a.content for a in artifacts}
    assert "app/models/task.py" in paths
    assert "docker-compose.yml" in paths
    assert "Dockerfile" in paths

    assert paths["app/models/task.py"] == "class Task:\n    id: int"
    assert paths["docker-compose.yml"] == "version: '3.8'\nservices:\n  web:\n    image: app:latest"
    assert paths["Dockerfile"] == "FROM python:3.11\nWORKDIR /app"


def test_handles_no_code_blocks_returns_empty_list():
    llm_output = (
        "### Implementation Summary:\n"
        "The implementation was analyzed, but no code was generated because the user requested an answer."
    )

    artifacts = extract_code_artifacts(llm_output)
    assert artifacts == [], "Should return empty list when no code blocks are present, NEVER dump raw prose into main.py"
