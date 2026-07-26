"""
Integration tests — /api/v1/admin/users
Covers: auth guard, empty list, user list with required fields, plan defaults.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    return patch("app.core.deps.settings", mock)


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_users_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/users")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_users_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── List users ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_users_valid_key_returns_200():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_users_empty_db_returns_empty_list():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    assert r.json() == []


@pytest.mark.asyncio
async def test_admin_users_shows_registered_user():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "listeduser@test.com", "password": "StrongPass123!"},
            )
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    users = r.json()
    assert len(users) == 1
    assert users[0]["email"] == "listeduser@test.com"


@pytest.mark.asyncio
async def test_admin_users_response_has_required_fields():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "fields@test.com", "password": "StrongPass123!"},
            )
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    user = r.json()[0]
    for key in (
        "id",
        "email",
        "is_active",
        "plan",
        "plan_name",
        "subscription_status",
        "subscription_since",
    ):
        assert key in user, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_admin_users_no_subscription_shows_gratuit():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "free@test.com", "password": "StrongPass123!"},
            )
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    user = r.json()[0]
    assert user["plan"] == "Gratuit"
    assert user["plan_name"] is None
    assert user["subscription_status"] is None
    assert user["subscription_since"] is None


@pytest.mark.asyncio
async def test_admin_users_multiple_users_ordered_by_id_desc():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "first@test.com", "password": "StrongPass123!"},
            )
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "second@test.com", "password": "StrongPass123!"},
            )
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    users = r.json()
    assert len(users) == 2
    # Ordered by id desc: most recently registered user first
    assert users[0]["id"] > users[1]["id"]


# ── PATCH /{user_id}/rssi ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_toggles_flag():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "rssi@test.com", "password": "StrongPass123!"},
            )
            users_r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
            user_id = users_r.json()[0]["id"]

            r = await c.patch(
                f"{BASE}/admin/users/{user_id}/rssi",
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    assert r.json()["id"] == user_id
    assert r.json()["is_rssi_consultant"] is True


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_toggles_back():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/auth/register",
                json={"email": "rssi2@test.com", "password": "StrongPass123!"},
            )
            users_r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
            user_id = users_r.json()[0]["id"]

            await c.patch(
                f"{BASE}/admin/users/{user_id}/rssi",
                headers={"x-admin-key": "test-secret-key"},
            )
            r = await c.patch(
                f"{BASE}/admin/users/{user_id}/rssi",
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    assert r.json()["is_rssi_consultant"] is False


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_unknown_user_returns_404():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(
                f"{BASE}/admin/users/99999/rssi",
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_no_key_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"{BASE}/admin/users/1/rssi")
    assert r.status_code == 403


# ── PATCH /{user_id}/plan (override admin sans Stripe) ──────────────────────────


async def _seed_plan(
    name: str,
    *,
    display_name: str,
    price_eur: int,
    max_sites: int,
    scan_interval_days: int,
    tier_level: int,
    allow_conformity_export: bool,
) -> None:
    from app.core.database import AsyncSessionLocal
    from app.models.plan import Plan

    async with AsyncSessionLocal() as db:
        db.add(
            Plan(
                name=name,
                display_name=display_name,
                price_eur=price_eur,
                max_sites=max_sites,
                scan_interval_days=scan_interval_days,
                tier_level=tier_level,
                stripe_price_id="",
                is_active=True,
                allow_conformity_export=allow_conformity_export,
            )
        )
        await db.commit()


async def _register_and_get_id(c: AsyncClient, email: str) -> int:
    await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    users_r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    return next(u["id"] for u in users_r.json() if u["email"] == email)


@pytest.mark.asyncio
async def test_set_user_plan_assigns_plan_without_stripe():
    await _seed_plan(
        "starter",
        display_name="Starter",
        price_eur=4900,
        max_sites=5,
        scan_interval_days=1,
        tier_level=2,
        allow_conformity_export=True,
    )
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            user_id = await _register_and_get_id(c, "setplan@test.com")
            r = await c.patch(
                f"{BASE}/admin/users/{user_id}/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "starter"},
            )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == user_id
    assert body["plan_name"] == "starter"
    assert body["plan"] == "Starter"
    assert body["max_sites"] == 5
    assert body["scan_interval_days"] == 1
    assert body["allow_conformity_export"] is True


@pytest.mark.asyncio
async def test_set_user_plan_reflected_in_user_list():
    await _seed_plan(
        "pro",
        display_name="Pro",
        price_eur=14900,
        max_sites=25,
        scan_interval_days=1,
        tier_level=3,
        allow_conformity_export=True,
    )
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            user_id = await _register_and_get_id(c, "reflect@test.com")
            await c.patch(
                f"{BASE}/admin/users/{user_id}/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "pro"},
            )
            users_r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    user = next(u for u in users_r.json() if u["id"] == user_id)
    assert user["plan_name"] == "pro"
    assert user["subscription_status"] == "active"


@pytest.mark.asyncio
async def test_set_user_plan_downgrade_switches_plan():
    await _seed_plan(
        "pro",
        display_name="Pro",
        price_eur=14900,
        max_sites=25,
        scan_interval_days=1,
        tier_level=3,
        allow_conformity_export=True,
    )
    await _seed_plan(
        "free",
        display_name="Gratuit",
        price_eur=0,
        max_sites=1,
        scan_interval_days=30,
        tier_level=1,
        allow_conformity_export=False,
    )
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            user_id = await _register_and_get_id(c, "downgrade@test.com")
            await c.patch(
                f"{BASE}/admin/users/{user_id}/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "pro"},
            )
            r = await c.patch(
                f"{BASE}/admin/users/{user_id}/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "free"},
            )
            users_r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    assert r.json()["plan_name"] == "free"
    user = next(u for u in users_r.json() if u["id"] == user_id)
    assert user["plan_name"] == "free"


@pytest.mark.asyncio
async def test_set_user_plan_unknown_user_returns_404():
    await _seed_plan(
        "starter",
        display_name="Starter",
        price_eur=4900,
        max_sites=5,
        scan_interval_days=1,
        tier_level=2,
        allow_conformity_export=True,
    )
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(
                f"{BASE}/admin/users/99999/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "starter"},
            )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_set_user_plan_unknown_plan_returns_404():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            user_id = await _register_and_get_id(c, "noplan@test.com")
            r = await c.patch(
                f"{BASE}/admin/users/{user_id}/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "does-not-exist"},
            )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_set_user_plan_no_key_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"{BASE}/admin/users/1/plan", json={"plan_name": "starter"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_set_user_plan_rejects_extra_fields():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            user_id = await _register_and_get_id(c, "extra@test.com")
            r = await c.patch(
                f"{BASE}/admin/users/{user_id}/plan",
                headers={"x-admin-key": "test-secret-key"},
                json={"plan_name": "starter", "price_eur": 0},
            )
    assert r.status_code == 422
