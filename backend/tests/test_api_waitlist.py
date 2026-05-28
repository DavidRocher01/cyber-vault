"""
Integration tests — /api/v1/api-waitlist
Covers: POST (201 new entry, 409 duplicate), GET /count.
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"

_PAYLOAD = {"email": "dev@example.com", "role": "msp", "company": "Acme"}


# ── POST /api-waitlist ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_join_waitlist_returns_201_with_count():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/api-waitlist", json=_PAYLOAD)
    assert r.status_code == 201
    assert r.json()["count"] == 1


@pytest.mark.asyncio
async def test_join_waitlist_duplicate_email_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/api-waitlist", json=_PAYLOAD)
        r = await c.post(f"{BASE}/api-waitlist", json=_PAYLOAD)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_join_waitlist_count_increments():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.post(f"{BASE}/api-waitlist", json={**_PAYLOAD, "email": "a@a.com"})
        r2 = await c.post(f"{BASE}/api-waitlist", json={**_PAYLOAD, "email": "b@b.com"})
    assert r1.json()["count"] == 1
    assert r2.json()["count"] == 2


# ── GET /api-waitlist/count ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_count_empty_returns_zero():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/api-waitlist/count")
    assert r.status_code == 200
    assert r.json()["count"] == 0


@pytest.mark.asyncio
async def test_get_count_after_signup_returns_one():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/api-waitlist", json=_PAYLOAD)
        r = await c.get(f"{BASE}/api-waitlist/count")
    assert r.json()["count"] == 1
