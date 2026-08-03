"""
Integration tests — /api/v1/admin/users
Covers: auth guard, empty list, user list with required fields, plan defaults.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_admin_users_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/users")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_users_wrong_key_returns_403(entetes_non_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/users", headers=entetes_non_admin)
    assert r.status_code == 403


# ── List users ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_users_valid_key_returns_200(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_users_base_sans_inscrit(entetes_admin):
    """Depuis que le droit est porte par un compte, une base « vide » contient
    quand meme l'administrateur qui interroge."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    comptes = r.json()
    assert [u["email"] for u in comptes] == ["admin@test.com"]
    assert comptes[0]["is_admin"] is True


@pytest.mark.asyncio
async def test_admin_users_shows_registered_user(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "listeduser@test.com", "password": "StrongPass123!"},
        )
        r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    assert r.status_code == 200
    users = r.json()
    # L'administrateur figure aussi dans la liste : deux comptes, le plus recent
    # en tete (tri par id decroissant).
    assert len(users) == 2
    assert users[0]["email"] == "listeduser@test.com"


@pytest.mark.asyncio
async def test_admin_users_response_has_required_fields(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "fields@test.com", "password": "StrongPass123!"},
        )
        r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
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
async def test_admin_users_no_subscription_shows_gratuit(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "free@test.com", "password": "StrongPass123!"},
        )
        r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    user = r.json()[0]
    assert user["plan"] == "Gratuit"
    assert user["plan_name"] is None
    assert user["subscription_status"] is None
    assert user["subscription_since"] is None


@pytest.mark.asyncio
async def test_admin_users_multiple_users_ordered_by_id_desc(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "first@test.com", "password": "StrongPass123!"},
        )
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "second@test.com", "password": "StrongPass123!"},
        )
        r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    users = r.json()
    # Trois comptes : les deux inscrits ici, plus l'administrateur.
    assert len(users) == 3
    # Ordered by id desc: most recently registered user first
    assert users[0]["id"] > users[1]["id"] > users[2]["id"]


# ── PATCH /{user_id}/rssi ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_toggles_flag(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "rssi@test.com", "password": "StrongPass123!"},
        )
        users_r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
        user_id = users_r.json()[0]["id"]

        r = await c.patch(
            f"{BASE}/admin/users/{user_id}/rssi",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert r.json()["id"] == user_id
    assert r.json()["is_rssi_consultant"] is True


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_toggles_back(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "rssi2@test.com", "password": "StrongPass123!"},
        )
        users_r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
        user_id = users_r.json()[0]["id"]

        await c.patch(
            f"{BASE}/admin/users/{user_id}/rssi",
            headers=entetes_admin,
        )
        r = await c.patch(
            f"{BASE}/admin/users/{user_id}/rssi",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert r.json()["is_rssi_consultant"] is False


@pytest.mark.asyncio
async def test_toggle_rssi_consultant_unknown_user_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(
            f"{BASE}/admin/users/99999/rssi",
            headers=entetes_admin,
        )
    assert r.status_code == 404


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_toggle_rssi_consultant_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"{BASE}/admin/users/1/rssi")
    assert r.status_code == 401


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


async def _register_and_get_id(c: AsyncClient, email: str, entetes: dict) -> int:
    """Les en-tetes sont passes en argument : ce helper n'est pas un test, il ne
    peut donc pas recevoir la fixture directement."""
    await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    users_r = await c.get(f"{BASE}/admin/users", headers=entetes)
    return next(u["id"] for u in users_r.json() if u["email"] == email)


@pytest.mark.asyncio
async def test_set_user_plan_assigns_plan_without_stripe(entetes_admin):
    await _seed_plan(
        "starter",
        display_name="Starter",
        price_eur=4900,
        max_sites=5,
        scan_interval_days=1,
        tier_level=2,
        allow_conformity_export=True,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        user_id = await _register_and_get_id(c, "setplan@test.com", entetes_admin)
        r = await c.patch(
            f"{BASE}/admin/users/{user_id}/plan",
            headers=entetes_admin,
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
async def test_set_user_plan_reflected_in_user_list(entetes_admin):
    await _seed_plan(
        "pro",
        display_name="Pro",
        price_eur=14900,
        max_sites=25,
        scan_interval_days=1,
        tier_level=3,
        allow_conformity_export=True,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        user_id = await _register_and_get_id(c, "reflect@test.com", entetes_admin)
        await c.patch(
            f"{BASE}/admin/users/{user_id}/plan",
            headers=entetes_admin,
            json={"plan_name": "pro"},
        )
        users_r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    user = next(u for u in users_r.json() if u["id"] == user_id)
    assert user["plan_name"] == "pro"
    assert user["subscription_status"] == "active"


@pytest.mark.asyncio
async def test_set_user_plan_downgrade_switches_plan(entetes_admin):
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        user_id = await _register_and_get_id(c, "downgrade@test.com", entetes_admin)
        await c.patch(
            f"{BASE}/admin/users/{user_id}/plan",
            headers=entetes_admin,
            json={"plan_name": "pro"},
        )
        r = await c.patch(
            f"{BASE}/admin/users/{user_id}/plan",
            headers=entetes_admin,
            json={"plan_name": "free"},
        )
        users_r = await c.get(f"{BASE}/admin/users", headers=entetes_admin)
    assert r.status_code == 200
    assert r.json()["plan_name"] == "free"
    user = next(u for u in users_r.json() if u["id"] == user_id)
    assert user["plan_name"] == "free"


@pytest.mark.asyncio
async def test_set_user_plan_unknown_user_returns_404(entetes_admin):
    await _seed_plan(
        "starter",
        display_name="Starter",
        price_eur=4900,
        max_sites=5,
        scan_interval_days=1,
        tier_level=2,
        allow_conformity_export=True,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(
            f"{BASE}/admin/users/99999/plan",
            headers=entetes_admin,
            json={"plan_name": "starter"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_set_user_plan_unknown_plan_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        user_id = await _register_and_get_id(c, "noplan@test.com", entetes_admin)
        r = await c.patch(
            f"{BASE}/admin/users/{user_id}/plan",
            headers=entetes_admin,
            json={"plan_name": "does-not-exist"},
        )
    assert r.status_code == 404


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_set_user_plan_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.patch(f"{BASE}/admin/users/1/plan", json={"plan_name": "starter"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_set_user_plan_rejects_extra_fields(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        user_id = await _register_and_get_id(c, "extra@test.com", entetes_admin)
        r = await c.patch(
            f"{BASE}/admin/users/{user_id}/plan",
            headers=entetes_admin,
            json={"plan_name": "starter", "price_eur": 0},
        )
    assert r.status_code == 422
