import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_docs_page():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/docs")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_page():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/login")
        assert resp.status_code == 200
        assert "تسجيل الدخول" in resp.text


@pytest.mark.asyncio
async def test_register_page():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/register")
        assert resp.status_code == 200
        assert "تسجيل جديد" in resp.text


@pytest.mark.asyncio
async def test_register_user():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        resp = await client.post("/auth/register", data={
            "name": "مصدر تجريبي",
            "email": "test@test.com",
            "password": "test123456",
            "confirm_password": "test123456",
        })
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/dashboard"


@pytest.mark.asyncio
async def test_login():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        resp = await client.post("/auth/login", data={
            "email": "test@test.com",
            "password": "test123456",
        })
        assert resp.status_code == 302
        assert resp.headers.get("location") == "/dashboard"
        assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_dashboard_requires_auth():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as client:
        resp = await client.get("/dashboard")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_with_auth():
    from app.main import app
    from app.core.security import create_access_token
    token = create_access_token({"sub": "1", "role": "admin"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert "لوحة التحكم" in resp.text or "مرحباً" in resp.text
