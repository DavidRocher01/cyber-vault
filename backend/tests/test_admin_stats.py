"""
Integration tests — /api/v1/admin/stats
Covers: auth guard, response structure, data reflects DB state.
"""
import pytest
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    return patch("app.api.v1.endpoints.admin_stats.settings", mock)


# ── Auth guard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/stats")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/stats", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── Response structure ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats_valid_key_returns_200():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/stats", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_stats_has_all_required_keys():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/stats", headers={"x-admin-key": "test-secret-key"})
    data = r.json()
    for key in (
        "users_total", "active_subscriptions", "newsletter_subscribers",
        "bookings_this_month", "new_contacts", "recent_contacts", "recent_bookings",
    ):
        assert key in data, f"Missing key: {key}"
    assert isinstance(data["recent_contacts"], list)
    assert isinstance(data["recent_bookings"], list)


@pytest.mark.asyncio
async def test_admin_stats_empty_db_returns_zeros():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/stats", headers={"x-admin-key": "test-secret-key"})
    data = r.json()
    assert data["users_total"] == 0
    assert data["active_subscriptions"] == 0
    assert data["new_contacts"] == 0
    assert data["recent_contacts"] == []
    assert data["recent_bookings"] == []


@pytest.mark.asyncio
async def test_admin_stats_counts_registered_user():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/auth/register", json={
                "email": "stats_user@test.com", "password": "StrongPass123!"
            })
            r = await c.get(f"{BASE}/admin/stats", headers={"x-admin-key": "test-secret-key"})
    assert r.json()["users_total"] == 1


@pytest.mark.asyncio
async def test_admin_stats_counts_new_contact_message():
    with _admin_settings():
        contact_settings = MagicMock()
        contact_settings.ADMIN_API_KEY = "test-secret-key"
        contact_settings.CONTACT_EMAIL = "admin@test.com"
        with patch("app.api.v1.endpoints.contact.settings", contact_settings):
            with patch("app.api.v1.endpoints.contact.send_contact_email"):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    await c.post(f"{BASE}/contact", json={
                        "name": "Test User",
                        "email": "test@example.com",
                        "need_type": "audit-flash",
                        "message": "Message de test assez long pour passer la validation.",
                    })
                    r = await c.get(f"{BASE}/admin/stats", headers={"x-admin-key": "test-secret-key"})
    assert r.json()["new_contacts"] == 1
    assert len(r.json()["recent_contacts"]) == 1
