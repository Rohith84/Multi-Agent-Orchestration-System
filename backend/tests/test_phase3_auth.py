import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.database import init_db, engine


@pytest.mark.asyncio(loop_scope="module")
async def test_auth_flow():
    """Verify login and route protection behaviors."""
    await engine.dispose()
    await init_db()
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Login with valid credentials
        login_payload = {
            "username": "admin@enterprise.com",
            "password": "admin123"
        }
        login_res = await ac.post(
            "/api/auth/login",
            data=login_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert login_res.status_code == 200
        token_data = login_res.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        token = token_data["access_token"]

        # 2. Login with invalid credentials
        bad_login_payload = {
            "username": "admin@enterprise.com",
            "password": "wrongpassword"
        }
        bad_login_res = await ac.post(
            "/api/auth/login",
            data=bad_login_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert bad_login_res.status_code == 401

        # 3. Request protected endpoint (/api/chat) without token
        unauth_res = await ac.post("/api/chat", json={"message": "Hello"})
        assert unauth_res.status_code == 401

        # 4. Request protected endpoint with invalid token
        invalid_res = await ac.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer badtoken123"}
        )
        assert invalid_res.status_code == 401

        # 5. Request protected endpoint with valid token
        auth_res = await ac.post(
            "/api/chat",
            json={"message": "Hello"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert auth_res.status_code == 200
        assert "response" in auth_res.json()
