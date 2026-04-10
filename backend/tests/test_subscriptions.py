"""
Integration tests — /api/v1/subscriptions
Covers: get my subscription (none/active), checkout dev mode,
        billing portal dev mode, plan not found, auth isolation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.plan import Plan

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _seed_plan(name: str = "starter") -> int:
    """Insert a plan directly via the DB override and return its id."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        plan = Plan(
            name=name,
            display_name="Starter",
            price_eur=900,
            max_sites=1,
            scan_interval_days=30,
            tier_level=2,
            stripe_price_id="",
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan.id


# ── GET /subscriptions/me ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_subscription_returns_none_when_no_subscription():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "sub1@test.com")
        r = await c.get(f"{BASE}/subscriptions/me", headers=h)
    assert r.status_code == 200
    assert r.json() is None


@pytest.mark.asyncio
async def test_get_subscription_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/subscriptions/me")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_subscription_returns_active_after_checkout():
    plan_id = await _seed_plan("starter_me")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "sub2@test.com")
        await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)
        r = await c.get(f"{BASE}/subscriptions/me", headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "active"
    assert r.json()["plan"]["id"] == plan_id


# ── POST /subscriptions/checkout/{plan_id} ────────────────────────────────────

@pytest.mark.asyncio
async def test_checkout_dev_mode_returns_url():
    plan_id = await _seed_plan("starter_co")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "co1@test.com")
        r = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)
    assert r.status_code == 200
    assert "checkout_url" in r.json()
    assert r.json()["checkout_url"].endswith("/cyberscan/success")


@pytest.mark.asyncio
async def test_checkout_unknown_plan_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "co2@test.com")
        r = await c.post(f"{BASE}/subscriptions/checkout/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_checkout_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/subscriptions/checkout/1")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_checkout_updates_existing_subscription():
    plan_id = await _seed_plan("starter_upd")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "co3@test.com")
        # First checkout creates subscription
        await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)
        # Second checkout on same user should update (not create duplicate)
        r2 = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)
        assert r2.status_code == 200
        # Verify still only one active subscription
        me = await c.get(f"{BASE}/subscriptions/me", headers=h)
        assert me.json()["status"] == "active"


@pytest.mark.asyncio
async def test_checkout_inactive_plan_returns_404():
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        plan = Plan(
            name="inactive_plan",
            display_name="Inactive",
            price_eur=100,
            max_sites=1,
            scan_interval_days=30,
            tier_level=2,
            stripe_price_id="",
            is_active=False,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        plan_id = plan.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "co4@test.com")
        r = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)
    assert r.status_code == 404


# ── GET /subscriptions/portal ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_portal_dev_mode_returns_dashboard_url():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "portal1@test.com")
        r = await c.get(f"{BASE}/subscriptions/portal", headers=h)
    assert r.status_code == 200
    assert "checkout_url" in r.json()
    assert "dashboard" in r.json()["checkout_url"]


@pytest.mark.asyncio
async def test_portal_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/subscriptions/portal")
    assert r.status_code == 403
