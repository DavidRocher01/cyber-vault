"""Tests for P6 (consultant profile) and P7 (CSV export)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.user import User

BASE = "/api/v1"


async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(
        f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"}
    )
    r = await http_client.post(
        f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _auth_consultant(http_client: AsyncClient, email: str) -> dict:
    """Register, login, and mark user as RSSI consultant."""
    import app.core.database as _db_mod

    headers = await _auth(http_client, email)
    async with _db_mod.AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers


async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Acme") -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_action(
    http_client: AsyncClient,
    headers: dict,
    client_id: int,
    title: str,
    priority: str = "medium",
) -> dict:
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/actions",
        json={"title": title, "priority": priority},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── P6 — Consultant profile ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_profile_get_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/profile")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_profile_get_non_consultant_forbidden(http_client: AsyncClient):
    h = await _auth(http_client, "profile_nc@test.com")
    r = await http_client.get(f"{BASE}/rssi/profile", headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_profile_patch_non_consultant_forbidden(http_client: AsyncClient):
    h = await _auth(http_client, "profile_nc2@test.com")
    r = await http_client.patch(f"{BASE}/rssi/profile", json={"display_name": "Hacker"}, headers=h)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_profile_initial_values_are_null(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "profile_init@test.com")
    r = await http_client.get(f"{BASE}/rssi/profile", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "profile_init@test.com"
    assert data["display_name"] is None
    assert data["company_name"] is None
    assert data["phone"] is None


@pytest.mark.asyncio
async def test_profile_patch_all_fields(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "profile_patch@test.com")
    r = await http_client.patch(
        f"{BASE}/rssi/profile",
        json={
            "display_name": "Jean Dupont",
            "company_name": "CyberConseil",
            "phone": "+33600000000",
        },
        headers=h,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["display_name"] == "Jean Dupont"
    assert data["company_name"] == "CyberConseil"
    assert data["phone"] == "+33600000000"


@pytest.mark.asyncio
async def test_profile_patch_partial(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "profile_partial@test.com")
    await http_client.patch(f"{BASE}/rssi/profile", json={"display_name": "Alice"}, headers=h)
    r = await http_client.get(f"{BASE}/rssi/profile", headers=h)
    assert r.status_code == 200
    assert r.json()["display_name"] == "Alice"
    assert r.json()["company_name"] is None  # untouched


@pytest.mark.asyncio
async def test_profile_patch_empty_string_clears_field(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "profile_clear@test.com")
    await http_client.patch(f"{BASE}/rssi/profile", json={"company_name": "ABC"}, headers=h)
    await http_client.patch(f"{BASE}/rssi/profile", json={"company_name": ""}, headers=h)
    r = await http_client.get(f"{BASE}/rssi/profile", headers=h)
    assert r.json()["company_name"] is None


@pytest.mark.asyncio
async def test_profile_get_returns_email(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "profile_email@test.com")
    r = await http_client.get(f"{BASE}/rssi/profile", headers=h)
    assert r.json()["email"] == "profile_email@test.com"


# ── P7 — CSV export ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_export_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/999/actions/export")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_csv_export_unknown_client_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "csv_404@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999/actions/export", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_csv_export_empty_has_header_only(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "csv_empty@test.com")
    c = await _create_client(http_client, h, "CSV Empty Client")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/actions/export", headers=h)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.content.decode("utf-8-sig").splitlines()
    assert len(lines) == 1


@pytest.mark.asyncio
async def test_csv_export_header_columns(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "csv_hdr@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/actions/export", headers=h)
    header = r.content.decode("utf-8-sig").splitlines()[0]
    assert "Titre" in header
    assert "Priorité" in header
    assert "Statut" in header
    assert "Responsable" in header
    assert "Échéance" in header


@pytest.mark.asyncio
async def test_csv_export_contains_actions(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "csv_data@test.com")
    c = await _create_client(http_client, h)
    await _create_action(http_client, h, c["id"], "Mettre à jour le firewall", "high")
    await _create_action(http_client, h, c["id"], "Former les équipes", "low")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/actions/export", headers=h)
    content = r.content.decode("utf-8-sig")
    assert "Mettre à jour le firewall" in content
    assert "Former les équipes" in content
    assert "Haute" in content
    assert "Basse" in content


@pytest.mark.asyncio
async def test_csv_export_cross_user_isolation(http_client: AsyncClient):
    h1 = await _auth_consultant(http_client, "csv_u1@test.com")
    h2 = await _auth_consultant(http_client, "csv_u2@test.com")
    c = await _create_client(http_client, h1, "Client U1")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/actions/export", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_csv_export_uses_french_labels(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "csv_fr@test.com")
    c = await _create_client(http_client, h)
    await _create_action(http_client, h, c["id"], "Action critique", "critical")

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/actions/export", headers=h)
    content = r.content.decode("utf-8-sig")
    assert "Critique" in content
    assert "Ouverte" in content
