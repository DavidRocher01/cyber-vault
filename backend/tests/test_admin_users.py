"""
Integration tests — /api/v1/admin/users
Covers: auth guard, empty list, user list with required fields, plan defaults.
"""
import pytest
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    return patch("app.api.v1.endpoints.admin_users.settings", mock)


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
            await c.post(f"{BASE}/auth/register", json={
                "email": "listeduser@test.com", "password": "StrongPass123!"
            })
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    users = r.json()
    assert len(users) == 1
    assert users[0]["email"] == "listeduser@test.com"


@pytest.mark.asyncio
async def test_admin_users_response_has_required_fields():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/auth/register", json={
                "email": "fields@test.com", "password": "StrongPass123!"
            })
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    user = r.json()[0]
    for key in ("id", "email", "is_active", "plan", "plan_name", "subscription_status", "subscription_since"):
        assert key in user, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_admin_users_no_subscription_shows_gratuit():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/auth/register", json={
                "email": "free@test.com", "password": "StrongPass123!"
            })
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
            await c.post(f"{BASE}/auth/register", json={"email": "first@test.com", "password": "StrongPass123!"})
            await c.post(f"{BASE}/auth/register", json={"email": "second@test.com", "password": "StrongPass123!"})
            r = await c.get(f"{BASE}/admin/users", headers={"x-admin-key": "test-secret-key"})
    users = r.json()
    assert len(users) == 2
    # Ordered by id desc: most recently registered user first
    assert users[0]["id"] > users[1]["id"]
