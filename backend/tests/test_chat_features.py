import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import init_db, engine


async def _get_auth_headers(ac: AsyncClient) -> dict[str, str]:
    login_res = await ac.post(
        "/api/auth/login",
        data={"username": "admin@enterprise.com", "password": "admin123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


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
    await engine.dispose()
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = await _get_auth_headers(ac)
        response = await ac.post("/api/chat", json={"message": "What is Python?"}, headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data


@pytest.mark.asyncio(loop_scope="module")
async def test_build_mode_workflow_started_event():
    """Verify Build mode (/api/agents/chat) emits workflow_started event with session_id."""
    await engine.dispose()
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        headers = await _get_auth_headers(ac)
        async with ac.stream("POST", "/api/agents/chat", json={"message": "Build hello world"}, headers=headers) as response:
            assert response.status_code == 200
            events = []
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    events.append(line)
                    if "workflow_started" in line:
                        break

            assert any("workflow_started" in e for e in events), "workflow_started SSE event was not emitted"
