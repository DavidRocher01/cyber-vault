"""
Integration tests — /api/v1/admin/stats
Covers: auth guard, response structure, data reflects DB state.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_stats_sans_authentification_401():
    """Le back-office ne repond plus a un anonyme : ce n'est plus une cle
    absente (403) mais une identite absente (401)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_stats_compte_ordinaire_403(entetes_non_admin):
    """Le cas qui compte : etre connecte ne suffit pas. Remplace l'ancien test
    « mauvaise cle », qui ne verifiait qu'une comparaison de chaines."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_non_admin)
    assert r.status_code == 403


# ── Response structure ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_stats_valid_key_returns_200(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_stats_has_all_required_keys(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    data = r.json()
    for key in (
        "users_total",
        "active_subscriptions",
        "newsletter_subscribers",
        "bookings_this_month",
        "new_contacts",
        "recent_contacts",
        "recent_bookings",
        "weekly_activity",
        "revenue_per_month",
    ):
        assert key in data, f"Missing key: {key}"
    assert isinstance(data["recent_contacts"], list)
    assert isinstance(data["recent_bookings"], list)
    assert isinstance(data["weekly_activity"], list)
    assert isinstance(data["revenue_per_month"], list)


@pytest.mark.asyncio
async def test_admin_stats_weekly_activity_has_8_buckets(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    buckets = r.json()["weekly_activity"]
    assert len(buckets) == 8
    for b in buckets:
        assert "label" in b
        assert "users" in b
        assert "scans" in b
        assert isinstance(b["users"], int)
        assert isinstance(b["scans"], int)


@pytest.mark.asyncio
async def test_admin_stats_revenue_per_month_has_6_buckets(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    buckets = r.json()["revenue_per_month"]
    assert len(buckets) == 6
    for b in buckets:
        assert "label" in b
        assert "cents" in b
        assert isinstance(b["cents"], int)


@pytest.mark.asyncio
async def test_admin_stats_weekly_activity_counts_new_user(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "weekly_user@test.com", "password": "StrongPass123!"},
        )
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    total_users = sum(b["users"] for b in r.json()["weekly_activity"])
    # Deux comptes : celui cree ici, et l'administrateur qui interroge — depuis
    # le retrait de la cle partagee, l'admin EST un utilisateur.
    assert total_users == 2


@pytest.mark.asyncio
async def test_admin_stats_base_sans_activite(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    data = r.json()
    # Un seul utilisateur : l'administrateur lui-meme. Une base « vide » n'est
    # plus vide de comptes depuis que le droit est porte par un compte.
    assert data["users_total"] == 1
    assert data["active_subscriptions"] == 0
    assert data["new_contacts"] == 0
    assert data["recent_contacts"] == []
    assert data["recent_bookings"] == []


@pytest.mark.asyncio
async def test_admin_stats_counts_registered_user(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "stats_user@test.com", "password": "StrongPass123!"},
        )
        r = await c.get(f"{BASE}/admin/stats", headers=entetes_admin)
    assert r.json()["users_total"] == 2  # l'inscrit + l'administrateur


@pytest.mark.asyncio
async def test_admin_stats_counts_new_contact_message(entetes_admin):
    contact_settings = MagicMock()
    contact_settings.ADMIN_API_KEY = "test-secret-key"
    contact_settings.CONTACT_EMAIL = "admin@test.com"
    with patch("app.api.v1.endpoints.contact.settings", contact_settings):
        with patch("app.api.v1.endpoints.contact.send_contact_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                await c.post(
                    f"{BASE}/contact",
                    json={
                        "name": "Test User",
                        "email": "test@example.com",
                        "need_type": "audit-flash",
                        "message": "Message de test assez long pour passer la validation.",
                    },
                )
                r = await c.get(
                    f"{BASE}/admin/stats",
                    headers=entetes_admin,
                )
    assert r.json()["new_contacts"] == 1
    assert len(r.json()["recent_contacts"]) == 1
