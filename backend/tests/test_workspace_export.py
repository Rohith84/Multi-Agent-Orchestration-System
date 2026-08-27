import uuid
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import init_db
from app.services.workspace_service import WorkspaceService


@pytest.mark.asyncio(loop_scope="module")
async def test_workspace_sessions_and_export():
    """Verify GET /api/workspace and GET /api/workspace/export-zip endpoints."""
    # Dispose of old connection pool to prevent closed event loop errors
    from app.db.database import engine
    await engine.dispose()

    await init_db()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        test_sid = uuid.uuid4()
        
        # 1. Write a test file in a new session to ensure we have content to list and export
        from app.db.database import async_session_factory
        async with async_session_factory() as session:
            service = WorkspaceService(session, session_id=test_sid)
            await service.write_file("test_export.py", "print('hello export')", language="python")

        # 2. Test active files listing for test_sid
        res_workspace = await ac.get(f"/api/workspace?session_id={test_sid}")
        assert res_workspace.status_code == 200
        data_files = res_workspace.json()
        assert len(data_files) > 0
        assert data_files[0]["file_path"] == "test_export.py"

        # 3. Test zip export for test_sid
        res_export = await ac.get(f"/api/workspace/export-zip?session_id={test_sid}")
        assert res_export.status_code == 200
        assert res_export.headers.get("content-type") == "application/zip"
        assert len(res_export.content) > 0
