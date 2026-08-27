import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import init_db
from app.services.workspace_service import WorkspaceService


@pytest.mark.asyncio(loop_scope="module")
async def test_workspace_sessions_and_export():
    """Verify GET /api/workspace/sessions and GET /api/workspace/export/{session_id}."""
    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Test sessions summary list
        res_sessions = await ac.get("/api/workspace/sessions")
        assert res_sessions.status_code == 200
        data_sessions = res_sessions.json()
        assert isinstance(data_sessions, list)

        # 2. Write a test file in a new session to ensure zip export works
        test_sid = uuid.uuid4()
        from app.db.database import async_session_factory
        async with async_session_factory() as session:
            service = WorkspaceService(session, session_id=test_sid)
            await service.write_file("test_export.py", "print('hello export')", language="python")

        # 3. Test zip export for test_sid
        res_export = await ac.get(f"/api/workspace/export/{test_sid}")
        assert res_export.status_code == 200
        assert res_export.headers.get("content-type") == "application/zip"
        assert len(res_export.content) > 0
