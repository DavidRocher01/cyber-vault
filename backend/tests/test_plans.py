"""
Integration tests — /api/v1/plans
Covers: list plans (public, empty DB, with seeded plans).
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _seed_plans():
    """Insert two test plans directly into the DB."""
    # Import at call time so the conftest patch of AsyncSessionLocal is visible
    from app.core.database import AsyncSessionLocal
    from app.models.plan import Plan
    async with AsyncSessionLocal() as db:
        db.add(Plan(
            name="starter", display_name="Starter", price_eur=900,
            max_sites=3, scan_interval_days=30, tier_level=2, is_active=True,
        ))
        db.add(Plan(
            name="pro", display_name="Pro", price_eur=2900,
            max_sites=10, scan_interval_days=7, tier_level=3, is_active=True,
        ))
        db.add(Plan(
            name="legacy", display_name="Legacy", price_eur=500,
            max_sites=1, scan_interval_days=60, tier_level=1, is_active=False,
        ))
        await db.commit()


@pytest.mark.asyncio
async def test_list_plans_empty_db():
    """No plans seeded → empty list."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_plans_returns_active_only():
    """Only is_active=True plans are returned."""
    await _seed_plans()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    data = r.json()
    assert r.status_code == 200
    assert len(data) == 2
    names = [p["name"] for p in data]
    assert "legacy" not in names
    assert "starter" in names
    assert "pro" in names


@pytest.mark.asyncio
async def test_list_plans_ordered_by_price():
    """Plans must be returned ordered by price_eur ascending."""
    await _seed_plans()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    prices = [p["price_eur"] for p in r.json()]
    assert prices == sorted(prices)


@pytest.mark.asyncio
async def test_list_plans_no_auth_required():
    """Plans endpoint is public — no Authorization header needed."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_list_plans_response_shape():
    """Each plan object has the expected keys."""
    await _seed_plans()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    plan = r.json()[0]
    for key in ("id", "name", "display_name", "price_eur", "max_sites", "scan_interval_days", "tier_level"):
        assert key in plan, f"Missing key: {key}"
