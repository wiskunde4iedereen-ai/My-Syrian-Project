import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from httpx import AsyncClient, ASGITransport

pytestmark = pytest.mark.asyncio


@pytest.fixture
def seed_exporter():
    from app.core.database import SessionLocal
    from app.models.exporter import Exporter
    from sqlalchemy import select
    db = SessionLocal()
    if not db.execute(select(Exporter)).scalar_one_or_none():
        db.add(Exporter(company_name="مصدر تجريبي", owner_name="مالك", email="ex@test.com"))
        db.commit()
    db.close()


def _login(c):
    """Helper: login as admin and return response."""
    import asyncio
    return c.post("/auth/login", data={"email": "admin@heya.gov.sy", "password": "admin123"}, follow_redirects=False)


@pytest.mark.asyncio
async def test_exporters_crud():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await _login(c)
        assert r.status_code == 302

        r = await c.get("/exporters")
        assert r.status_code == 200

        r = await c.post("/exporters/create", data={"company_name": "شركة النور", "owner_name": "أحمد", "email": "a@a.com", "phone": "123", "commercial_registry": "CR001", "address": "دمشق"})
        assert r.status_code == 302

        r = await c.get("/exporters")
        assert "شركة النور" in r.text

        r = await c.get("/exporters/1/edit")
        assert r.status_code == 200

        r = await c.post("/exporters/1/edit", data={"company_name": "شركة النور الجديدة", "owner_name": "أحمد", "email": "a@a.com", "phone": "123", "commercial_registry": "CR001", "address": "حلب"})
        assert r.status_code == 302

        r = await c.post("/exporters/1/delete")
        assert r.status_code == 302

        r = await c.get("/exporters")
        assert "شركة النور" not in r.text


@pytest.mark.asyncio
async def test_products_crud(seed_exporter):
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await _login(c)
        assert r.status_code == 302

        r = await c.post("/products/create", data={
            "name": "زيت زيتون", "category": "غذائي", "hs_code": "1509.10",
            "origin": "سوريا", "unit": "طن", "exporter_id": "1",
        })
        assert r.status_code == 302

        r = await c.get("/products")
        assert r.status_code == 200
        assert "زيت زيتون" in r.text


@pytest.mark.asyncio
async def test_markets_crud():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await _login(c)
        assert r.status_code == 302

        r = await c.get("/markets")
        assert r.status_code == 200

        r = await c.post("/markets/create", data={"country": "الإمارات", "city": "دبي", "requirements": "شهادة منشأ"})
        assert r.status_code == 302

        r = await c.get("/markets")
        assert "الإمارات" in r.text


@pytest.mark.asyncio
async def test_licenses_workflow(seed_exporter):
    from app.main import app
    from app.core.database import SessionLocal
    from app.models.product import Product
    from app.models.market import Market
    from sqlalchemy import select

    db = SessionLocal()
    if not db.execute(select(Product)).scalar_one_or_none():
        db.add(Product(name="زيت زيتون", category="غذائي", hs_code="1509.10", origin="سوريا", unit="طن", exporter_id=1))
    if not db.execute(select(Market)).scalar_one_or_none():
        db.add(Market(country="الإمارات"))
    db.commit()
    db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await _login(c)
        assert r.status_code == 302

        r = await c.get("/licenses")
        assert r.status_code == 200

        r = await c.post("/licenses/create", data={"product_id": "1", "exporter_id": "1", "market_id": "1", "notes": "استيراد زيت زيتون"})
        assert r.status_code == 302

        r = await c.get("/licenses")
        assert "قيد الانتظار" in r.text

        r = await c.post("/licenses/1/approve")
        assert r.status_code == 302

        r = await c.get("/licenses")
        assert "معتمد" in r.text


@pytest.mark.asyncio
async def test_finance_crud(seed_exporter):
    from app.main import app
    from app.core.database import SessionLocal
    from app.models.product import Product
    from app.models.market import Market
    from app.models.license import License
    from sqlalchemy import select
    from datetime import datetime, timezone

    db = SessionLocal()
    if not db.execute(select(Product)).scalar_one_or_none():
        db.add(Product(name="زيت زيتون", category="غذائي", hs_code="1509.10", origin="سوريا", unit="طن", exporter_id=1))
    if not db.execute(select(Market)).scalar_one_or_none():
        db.add(Market(country="الإمارات"))
    if not db.execute(select(License)).scalar_one_or_none():
        db.add(License(product_id=1, exporter_id=1, market_id=1, status="approved"))
    db.commit()
    db.close()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await _login(c)
        assert r.status_code == 302

        r = await c.get("/finance")
        assert r.status_code == 200

        r = await c.post("/finance/create", data={"license_id": "1", "exporter_id": "1", "amount": "5000", "fee_type": "رسوم ترخيص"})
        assert r.status_code == 302

        r = await c.get("/finance")
        assert "5000" in r.text

        r = await c.post("/finance/1/pay")
        assert r.status_code == 302


@pytest.mark.asyncio
async def test_documents_crud(seed_exporter):
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await _login(c)
        assert r.status_code == 302

        r = await c.get("/documents")
        assert r.status_code == 200

        r = await c.get("/documents/upload")
        assert r.status_code == 200
