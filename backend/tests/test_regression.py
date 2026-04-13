"""
Tests de non-régression — contrats API critiques.

Ces tests garantissent que les fonctionnalités clés ne régressent pas
lors des évolutions futures. Chaque test est lié à un comportement
précis qui a déjà été bugué ou modifié intentionnellement.

Catégories :
  - [AUTH]    Flux d'authentification (login, 2FA, tokens)
  - [NIS2]    Module conformité NIS2 (score, sauvegarde, isolation)
  - [SCAN]    Scans de sécurité (déclenchement, résultats)
  - [URLSCAN] Scanner URL (création, PDF)
  - [USER]    Profil utilisateur (export, suppression)
  - [API]     Contrats généraux (statuts HTTP, formats)
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str, password: str = "StrongPass123!") -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── [AUTH] Flux d'authentification ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_returns_201_with_access_token():
    """Régression : l'inscription doit retourner 201 + access_token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={
            "email": "reg_regr@test.com", "password": "StrongPass123!"
        })
    assert r.status_code == 201
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_returns_access_token():
    """Régression : le login standard doit retourner un access_token valide."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "login_regr@test.com", "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": "login_regr@test.com", "password": "StrongPass123!"})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401():
    """Régression : mauvais mot de passe → 401 (pas 200, pas 500)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "badpwd@test.com", "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": "badpwd@test.com", "password": "WrongPass!"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_without_token_returns_403():
    """Régression : tous les endpoints protégés renvoient 403 sans token."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        endpoints = [
            ("GET",  f"{BASE}/users/me"),
            ("GET",  f"{BASE}/nis2/me"),
            ("PUT",  f"{BASE}/nis2/me"),
            ("GET",  f"{BASE}/url-scans"),
            ("GET",  f"{BASE}/code-scans"),
        ]
        for method, url in endpoints:
            r = await c.request(method, url)
            assert r.status_code == 403, f"{method} {url} devrait retourner 403, got {r.status_code}"


@pytest.mark.asyncio
async def test_token_gives_access_to_user_me():
    """Régression : un token valide doit permettre d'accéder à /users/me."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "me_regr@test.com")
        r = await c.get(f"{BASE}/users/me", headers=h)
    assert r.status_code == 200
    assert "email" in r.json()


# ── [NIS2] Module conformité ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_nis2_score_formula_compliant_2pts_partial_1pt():
    """Régression : compliant=2pts, partial=1pt, max=2*N → score correct."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_formula@test.com")
        # 1 compliant (2pts) + 1 partial (1pt) sur 2 items scorables → (3/4)*100 = 75%
        r = await c.put(f"{BASE}/nis2/me", json={
            "items": {"rssi": "compliant", "policy": "partial"}
        }, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 75


@pytest.mark.asyncio
async def test_nis2_score_ignores_na_items():
    """Régression : les items NA ne doivent pas pénaliser le score."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_na_regr@test.com")
        # 1 compliant + beaucoup de NA → score doit être 100
        items = {"rssi": "compliant"}
        # Ajouter des NA pour les autres items
        r_get = await c.get(f"{BASE}/nis2/me", headers=h)
        all_ids = [item["id"] for cat in r_get.json()["categories"] for item in cat["items"]]
        for item_id in all_ids:
            if item_id != "rssi":
                items[item_id] = "na"
        r = await c.put(f"{BASE}/nis2/me", json={"items": items}, headers=h)
    assert r.json()["score"] == 100


@pytest.mark.asyncio
async def test_nis2_user_isolation_strict():
    """Régression : un utilisateur ne doit jamais voir les données d'un autre."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h_a = await _headers(c, "nis2_iso_a@test.com")
        h_b = await _headers(c, "nis2_iso_b@test.com")

        # User A : tout conforme
        r_get = await c.get(f"{BASE}/nis2/me", headers=h_a)
        all_ids = [i["id"] for cat in r_get.json()["categories"] for i in cat["items"]]
        await c.put(f"{BASE}/nis2/me",
                    json={"items": {i: "compliant" for i in all_ids}},
                    headers=h_a)

        # User B : rien sauvegardé → score doit être 0, pas 100
        r_b = await c.get(f"{BASE}/nis2/me", headers=h_b)
    assert r_b.json()["score"] == 0
    assert r_b.json()["items"] == {}


@pytest.mark.asyncio
async def test_nis2_categories_count_never_changes():
    """Régression : NIS2 doit toujours avoir exactement 10 catégories et 34 critères."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_count@test.com")
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    cats = r.json()["categories"]
    assert len(cats) == 10, f"Attendu 10 catégories, got {len(cats)}"
    total = sum(len(c["items"]) for c in cats)
    assert total == 34, f"Attendu 34 critères, got {total}"


# ── [SCAN] Scans de sécurité ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_trigger_returns_scan_id_in_body():
    """Régression : le déclenchement d'un scan doit retourner scan_id dans le body."""
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "scan_regr@test.com")
            with patch("app.api.v1.endpoints.sites._get_max_sites", return_value=5):
                site_r = await c.post(f"{BASE}/sites", json={"url": "https://example.com", "name": "Test"}, headers=h)
            site_id = site_r.json()["id"]
            r = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)
    assert r.status_code == 202
    assert "scan_id" in r.json()


@pytest.mark.asyncio
async def test_scan_unknown_site_returns_404_not_500():
    """Régression : site inexistant → 404, jamais 500."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "scan404@test.com")
        r = await c.post(f"{BASE}/scans/trigger/999999", headers=h)
    assert r.status_code == 404


# ── [URLSCAN] Scanner URL ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_url_scan_response_has_required_fields():
    """Régression : la réponse d'un scan URL doit contenir id, status, url."""
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urlregr@test.com")
            r = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
    assert r.status_code == 202
    body = r.json()
    assert "id" in body
    assert "status" in body
    assert "url" in body
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_url_scan_ftp_always_rejected():
    """Régression : les URLs ftp:// doivent toujours être rejetées (422)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlftp@test.com")
        r = await c.post(f"{BASE}/url-scans", json={"url": "ftp://files.example.com"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_url_scan_pdf_requires_done_status():
    """Régression : le PDF d'un scan URL non terminé doit retourner 404."""
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urlpdf_regr@test.com")
            r_scan = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
            scan_id = r_scan.json()["id"]
            r_pdf = await c.get(f"{BASE}/url-scans/{scan_id}/pdf", headers=h)
    assert r_pdf.status_code == 404


# ── [USER] Profil utilisateur ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_user_me_response_has_required_fields():
    """Régression : /users/me doit toujours retourner id, email, is_active."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "me_fields@test.com")
        r = await c.get(f"{BASE}/users/me", headers=h)
    body = r.json()
    assert "id" in body
    assert "email" in body
    assert "is_active" in body
    assert body["email"] == "me_fields@test.com"


@pytest.mark.asyncio
async def test_user_delete_removes_access():
    """Régression : après suppression du compte, le token ne doit plus fonctionner."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "del_regr@test.com")
        await c.delete(f"{BASE}/users/me", headers=h)
        r = await c.get(f"{BASE}/users/me", headers=h)
    assert r.status_code in (401, 403, 404)


# ── [API] Contrats généraux ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """Régression : /health doit toujours retourner 200 (utilisé par l'ALB)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_plans_endpoint_is_public():
    """Régression : GET /plans doit être accessible sans authentification."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/plans")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_duplicate_email_returns_409():
    """Régression : inscription avec email déjà existant → 409, jamais 500."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        payload = {"email": "dup_regr@test.com", "password": "StrongPass123!"}
        await c.post(f"{BASE}/auth/register", json=payload)
        r = await c.post(f"{BASE}/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_pagination_defaults_are_stable():
    """Régression : la pagination par défaut doit retourner page=1, per_page=10."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "pag_regr@test.com")
        r = await c.get(f"{BASE}/url-scans", headers=h)
    body = r.json()
    assert "page" in body
    assert "per_page" in body
    assert "total" in body
    assert "items" in body
    assert body["page"] == 1
