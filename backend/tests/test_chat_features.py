import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import init_db


@pytest.mark.asyncio(loop_scope="module")
async def test_ollama_runtime_endpoint():
    """Verify GET /api/ollama/runtime endpoint returns process classification."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/ollama/runtime")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "processor" in data
        assert "vram_mb" in data


@pytest.mark.asyncio(loop_scope="module")
async def test_ask_mode_endpoint_single_call():
    """Verify Ask mode calls single /api/chat endpoint."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/chat", json={"message": "What is Python?"})
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data


@pytest.mark.asyncio(loop_scope="module")
async def test_build_mode_workflow_started_event():
    """Verify Build mode (/api/agents/chat) emits workflow_started event with session_id."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/api/agents/chat", json={"message": "Build hello world"}) as response:
            assert response.status_code == 200
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    events.append(line)
                    if "workflow_started" in line:
                        break

            assert any("workflow_started" in e for e in events), "workflow_started SSE event was not emitted"
