import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


@pytest.fixture
def app():
    from app.main import app
    return app


async def test_profile_page(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as c:
        r = await c.post("/auth/login", data={"email": "admin@heya.gov.sy", "password": "admin123"})
        assert r.status_code == 302
        r = await c.get("/auth/profile")
        assert r.status_code == 200
        assert "الملف الشخصي" in r.text


async def test_change_password(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as c:
        r = await c.post("/auth/login", data={"email": "admin@heya.gov.sy", "password": "admin123"})
        assert r.status_code == 302
        r = await c.post("/auth/change-password", data={
            "current_password": "admin123",
            "new_password": "newadmin123",
            "confirm_password": "newadmin123",
        })
        assert r.status_code == 200
        assert "تم تغيير كلمة المرور بنجاح" in r.text
        r = await c.post("/auth/login", data={"email": "admin@heya.gov.sy", "password": "newadmin123"})
        assert r.status_code == 302
        r = await c.post("/auth/change-password", data={
            "current_password": "newadmin123",
            "new_password": "admin123",
            "confirm_password": "admin123",
        })
        assert r.status_code == 200
        assert "تم تغيير كلمة المرور بنجاح" in r.text


async def test_create_user_by_dev(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as c:
        r = await c.post("/auth/login", data={"email": "dev@heya.gov.sy", "password": "dev123"})
        assert r.status_code == 302
        r = await c.get("/admin/users/create")
        assert r.status_code == 200
        assert "إضافة مستخدم جديد" in r.text
        r = await c.post("/admin/users/create", data={
            "name": "موظف جديد",
            "email": "new@heya.gov.sy",
            "password": "temp123",
            "role_id": "5",
        })
        assert r.status_code == 200
        assert "تم إنشاء المستخدم" in r.text


async def test_new_user_must_change_password(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as c:
        r = await c.post("/auth/login", data={"email": "new@heya.gov.sy", "password": "temp123"})
        assert r.status_code == 302
        assert "auth/profile/change-password" in r.headers.get("location", "")
        r = await c.get("/auth/profile/change-password")
        assert r.status_code == 200
        r = await c.post("/auth/change-password", data={
            "current_password": "temp123",
            "new_password": "newpass456",
            "confirm_password": "newpass456",
        })
        assert r.status_code == 200
        assert "تم تغيير كلمة المرور بنجاح" in r.text
        r = await c.post("/auth/login", data={"email": "new@heya.gov.sy", "password": "newpass456"})
        assert r.status_code == 302
        assert r.headers.get("location") != "/auth/profile/change-password"


async def test_reset_password_by_dev(app):
    """Reset password of the newly created user (id=4, new@heya.gov.sy)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as c:
        r = await c.post("/auth/login", data={"email": "dev@heya.gov.sy", "password": "dev123"})
        assert r.status_code == 302
        r = await c.post("/admin/users/4/reset-password")
        assert r.status_code == 200
        assert "تم إعادة تعيين كلمة السر" in r.text


async def test_backup_page(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test", follow_redirects=False) as c:
        r = await c.post("/auth/login", data={"email": "dev@heya.gov.sy", "password": "dev123"})
        assert r.status_code == 302
        r = await c.get("/admin/backup")
        assert r.status_code == 200
        assert "النسخ الاحتياطي" in r.text
