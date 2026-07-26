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
        db.add(
            Plan(
                name="starter",
                display_name="Starter",
                price_eur=900,
                max_sites=3,
                scan_interval_days=30,
                tier_level=2,
                is_active=True,
            )
        )
        db.add(
            Plan(
                name="pro",
                display_name="Pro",
                price_eur=2900,
                max_sites=10,
                scan_interval_days=7,
                tier_level=3,
                is_active=True,
            )
        )
        db.add(
            Plan(
                name="legacy",
                display_name="Legacy",
                price_eur=500,
                max_sites=1,
                scan_interval_days=60,
                tier_level=1,
                is_active=False,
            )
        )
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
    for key in (
        "id",
        "name",
        "display_name",
        "price_eur",
        "price_eur_yearly",
        "yearly_available",
        "max_sites",
        "scan_interval_days",
        "tier_level",
        "allow_conformity_export",
    ):
        assert key in plan, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_list_plans_exposes_annual_billing_fields():
    """price_eur_yearly = mensuel x 10 (2 mois offerts) ; yearly_available suit le price_id annuel."""
    from app.core.database import AsyncSessionLocal
    from app.models.plan import Plan

    async with AsyncSessionLocal() as db:
        # Plan sans price_id annuel → facturation annuelle indisponible.
        db.add(
            Plan(
                name="starter",
                display_name="Starter",
                price_eur=4900,
                max_sites=5,
                scan_interval_days=1,
                tier_level=2,
                is_active=True,
            )
        )
        # Plan avec price_id annuel configuré → disponible.
        db.add(
            Plan(
                name="pro",
                display_name="Pro",
                price_eur=14900,
                max_sites=25,
                scan_interval_days=1,
                tier_level=3,
                stripe_price_id="price_pro_m",
                stripe_price_id_yearly="price_pro_y",
                is_active=True,
            )
        )
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    plans = {p["name"]: p for p in r.json()}

    assert plans["starter"]["price_eur_yearly"] == 49000  # 4900 x 10
    assert plans["starter"]["yearly_available"] is False
    assert plans["pro"]["price_eur_yearly"] == 149000  # 14900 x 10
    assert plans["pro"]["yearly_available"] is True
