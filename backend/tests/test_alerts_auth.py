import asyncio
import json
import os
import sys
import pytest
from httpx import AsyncClient, ASGITransport

# Ensure backend package root is on PYTHONPATH for imports
ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT_PATH not in sys.path:
    sys.path.insert(0, ROOT_PATH)

# Use a local SQLite test database for backend tests when Postgres is unavailable
DB_PATH = os.path.abspath(os.path.join(ROOT_PATH, "backend_test.db"))
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH.replace('\\', '/')}" )
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")

from app.main import app
from app.db.base import Base
from app.db.session import engine

async def _init_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(_init_test_db())

from app.core.config import settings

@pytest.mark.asyncio
async def test_alerts_auth_allow_when_no_secret(monkeypatch):
    # Ensure SIEM_SHARED_SECRET is empty for permissive mode
    monkeypatch.setattr(settings, "SIEM_SHARED_SECRET", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/alerts/", json={
            "event_type": "test",
            "severity": "low",
            "source": "unit-test",
            "payload": {"foo": "bar"},
            "description": "test"
        })
        assert resp.status_code in (200, 201)

@pytest.mark.asyncio
async def test_alerts_auth_require_token(monkeypatch):
    # Set a shared secret and assert requests without token fail
    monkeypatch.setattr(settings, "SIEM_SHARED_SECRET", "test_secret_123")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/alerts/", json={
            "event_type": "test",
            "severity": "low",
            "source": "unit-test",
            "payload": {"foo": "bar"},
            "description": "test"
        })
        assert resp.status_code == 401

        # Now try with Bearer token
        headers = {"Authorization": "Bearer test_secret_123"}
        resp2 = await ac.post("/api/alerts/", json={
            "event_type": "test",
            "severity": "low",
            "source": "unit-test",
            "payload": {"foo": "bar"},
            "description": "test"
        }, headers=headers)
        assert resp2.status_code in (200, 201)

        # And with X-API-Key
        headers2 = {"X-API-Key": "test_secret_123"}
        resp3 = await ac.post("/api/alerts/", json={
            "event_type": "test",
            "severity": "low",
            "source": "unit-test",
            "payload": {"foo": "bar"},
            "description": "test"
        }, headers=headers2)
        assert resp3.status_code in (200, 201)
