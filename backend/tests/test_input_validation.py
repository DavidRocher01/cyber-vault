"""
Tests de validation des entrées — frontières et cas limites.

Ces tests vérifient que l'API rejette correctement les entrées invalides
(422 Unprocessable Entity) et accepte les entrées valides aux limites.

Catégories :
  - [AUTH]   Validation des champs d'inscription/connexion
  - [SITES]  Validation des URLs de sites
  - [SCAN]   Validation des déclenchements de scan
  - [URLSCAN] Validation des URLs à analyser
  - [CODESCAN] Validation des repos
  - [NIS2]   Validation des statuts d'items
  - [PAGES]  Validation des paramètres de pagination
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str, password: str = "StrongPass123!") -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── [AUTH] Validation des champs d'inscription ────────────────────────────────

@pytest.mark.asyncio
async def test_register_missing_email_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={"password": "StrongPass123!"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_missing_password_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={"email": "valid@test.com"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_body_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_empty_email_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={"email": "", "password": "StrongPass123!"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_register_password_too_short_returns_422():
    """Mot de passe < 8 caractères doit être rejeté."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={"email": "short@test.com", "password": "Ab1!"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_email_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/login", json={"password": "StrongPass123!"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_password_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/login", json={"email": "valid@test.com"})
    assert r.status_code == 422


# ── [SITES] Validation des URLs ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_site_missing_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "site_val1@test.com")
        with patch("app.api.v1.endpoints.sites.get_active_plan", new=AsyncMock(return_value=MagicMock(max_sites=5))):
            r = await c.post(f"{BASE}/sites", json={"name": "Mon site"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_site_missing_name_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "site_val2@test.com")
        with patch("app.api.v1.endpoints.sites.get_active_plan", new=AsyncMock(return_value=MagicMock(max_sites=5))):
            r = await c.post(f"{BASE}/sites", json={"url": "https://example.com"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_site_no_protocol_autocorrected_to_https():
    """L'endpoint auto-corrige les URLs sans protocole → https:// est ajouté, 201 retourné."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "site_val3@test.com")
        with patch("app.api.v1.endpoints.sites.get_active_plan", new=AsyncMock(return_value=MagicMock(max_sites=5))):
            r = await c.post(f"{BASE}/sites", json={"url": "example.com", "name": "Test"}, headers=h)
    assert r.status_code == 201
    assert r.json()["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_create_site_ftp_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "site_val4@test.com")
        with patch("app.api.v1.endpoints.sites.get_active_plan", new=AsyncMock(return_value=MagicMock(max_sites=5))):
            r = await c.post(f"{BASE}/sites", json={"url": "ftp://files.example.com", "name": "FTP"}, headers=h)
    assert r.status_code == 422


# ── [URLSCAN] Validation des URLs ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_url_scan_missing_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlval1@test.com")
        r = await c.post(f"{BASE}/url-scans", json={}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scan_empty_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlval2@test.com")
        r = await c.post(f"{BASE}/url-scans", json={"url": ""}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scan_no_protocol_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlval3@test.com")
        r = await c.post(f"{BASE}/url-scans", json={"url": "evil.com"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scan_javascript_protocol_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlval4@test.com")
        r = await c.post(f"{BASE}/url-scans", json={"url": "javascript:alert(1)"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scan_valid_https_accepted():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urlval5@test.com")
            r = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
    assert r.status_code == 202


# ── [CODESCAN] Validation des repos ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_code_scan_missing_repo_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "codev1@test.com")
        r = await c.post(f"{BASE}/code-scans", json={}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_code_scan_invalid_repo_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "codev2@test.com")
        r = await c.post(f"{BASE}/code-scans", json={"repo_url": "not-a-url"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_code_scan_empty_repo_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "codev3@test.com")
        r = await c.post(f"{BASE}/code-scans", json={"repo_url": ""}, headers=h)
    assert r.status_code == 422


# ── [NIS2] Validation des statuts ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nis2_invalid_status_value_returns_422():
    """Un statut inconnu (ex : 'maybe') doit être rejeté."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2v1@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "maybe"}}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_nis2_missing_items_field_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2v2@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_nis2_items_not_dict_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2v3@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={"items": ["compliant"]}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_nis2_all_valid_statuses_accepted():
    """Tous les statuts valides (compliant, partial, non_compliant, na) doivent passer.
    Utilise des IDs d'items réels (niveau item, pas catégorie)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2v4@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={
            "items": {
                "rssi": "compliant",          # item réel — Gouvernance
                "mgmt_training": "partial",   # item réel — Gouvernance
                "incident_proc": "non_compliant",  # item réel — Incidents
                "anssi_notif": "na",          # item réel — Incidents
            }
        }, headers=h)
    assert r.status_code == 200


# ── [PAGES] Validation de la pagination ──────────────────────────────────────

@pytest.mark.asyncio
async def test_url_scans_negative_page_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "page1@test.com")
        r = await c.get(f"{BASE}/url-scans?page=-1", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scans_zero_page_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "page2@test.com")
        r = await c.get(f"{BASE}/url-scans?page=0", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scans_page_1_returns_200():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "page3@test.com")
        r = await c.get(f"{BASE}/url-scans?page=1&per_page=5", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["page"] == 1
    assert body["per_page"] == 5
