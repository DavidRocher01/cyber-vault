"""
Integration tests — /api/v1/sites
Covers: list, create, delete, quota enforcement, auth isolation,
        URL normalisation (http prefix auto-added).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_list_sites_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "s1@test.com")
        r = await c.get(f"{BASE}/sites", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_add_site_no_subscription_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "s2@test.com")
        r = await c.post(f"{BASE}/sites", json={"url": "https://mysite.com", "name": "My Site"}, headers=h)
    assert r.status_code == 403
    assert "Abonnement" in r.json()["detail"]


@pytest.mark.asyncio
async def test_add_site_with_mocked_quota():
    """Patch get_active_plan to allow 3 sites without a real subscription."""
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "s3@test.com")
            r = await c.post(f"{BASE}/sites", json={"url": "https://mysite.com", "name": "Site A"}, headers=h)
    assert r.status_code == 201
    assert r.json()["url"] == "https://mysite.com"
    assert r.json()["name"] == "Site A"


@pytest.mark.asyncio
async def test_add_site_url_gets_https_prefix():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "s4@test.com")
            r = await c.post(f"{BASE}/sites", json={"url": "example.com", "name": "No Scheme"}, headers=h)
    assert r.status_code == 201
    assert r.json()["url"].startswith("https://")


@pytest.mark.asyncio
async def test_delete_site():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "s5@test.com")
            created = await c.post(f"{BASE}/sites", json={"url": "https://del.com", "name": "Del"}, headers=h)
            site_id = created.json()["id"]

            r = await c.delete(f"{BASE}/sites/{site_id}", headers=h)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_other_user_site_returns_404():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner@test.com")
            created = await c.post(f"{BASE}/sites", json={"url": "https://private.com", "name": "X"}, headers=h1)
            site_id = created.json()["id"]

            h2 = await _headers(c, "attacker@test.com")
            r = await c.delete(f"{BASE}/sites/{site_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_quota_exceeded_returns_403():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=1)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "quota@test.com")
            await c.post(f"{BASE}/sites", json={"url": "https://first.com", "name": "First"}, headers=h)
            r = await c.post(f"{BASE}/sites", json={"url": "https://second.com", "name": "Second"}, headers=h)
    assert r.status_code == 403
    assert "Limite" in r.json()["detail"]


@pytest.mark.asyncio
async def test_sites_not_visible_to_other_users():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner2@test.com")
            await c.post(f"{BASE}/sites", json={"url": "https://secret.com", "name": "Secret"}, headers=h1)

            h2 = await _headers(c, "spy@test.com")
            r = await c.get(f"{BASE}/sites", headers=h2)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_unauthenticated_sites_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/sites")
    assert r.status_code == 401


# ── Protocol validation ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_site_ftp_protocol_returns_422():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "proto1@test.com")
            r = await c.post(f"{BASE}/sites", json={"url": "ftp://example.com", "name": "FTP"}, headers=h)
    assert r.status_code == 422
    assert "Protocole" in r.json()["detail"]


@pytest.mark.asyncio
async def test_add_site_javascript_protocol_returns_422():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "proto2@test.com")
            r = await c.post(f"{BASE}/sites", json={"url": "javascript:alert(1)", "name": "XSS"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_add_site_data_protocol_returns_422():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "proto3@test.com")
            r = await c.post(f"{BASE}/sites", json={"url": "data:text/html,<h1>x</h1>", "name": "Data"}, headers=h)
    assert r.status_code == 422


# ── RSSI client ID validation ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_site_unknown_rssi_client_returns_404():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "rssi_site1@test.com")
            r = await c.post(
                f"{BASE}/sites",
                json={"url": "https://example.com", "name": "Tenant site", "rssi_client_id": 99999},
                headers=h,
            )
    assert r.status_code == 404
    assert "RSSI" in r.json()["detail"]


# ── Subdomains endpoint ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_site_subdomains_site_not_found_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "sub1@test.com")
        r = await c.get(f"{BASE}/sites/99999/subdomains", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_site_subdomains_no_scan_returns_empty():
    with patch("app.api.v1.endpoints.sites.get_effective_max_sites", new=AsyncMock(return_value=3)):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "sub2@test.com")
            created = await c.post(
                f"{BASE}/sites", json={"url": "https://nosubdom.com", "name": "No scan"}, headers=h
            )
            site_id = created.json()["id"]
            r = await c.get(f"{BASE}/sites/{site_id}/subdomains", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["subdomains"] == []
    assert data["zone_transfer"] is None
    assert data["scan_date"] is None
