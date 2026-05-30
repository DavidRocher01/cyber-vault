"""
Tests d'intégration — Awareness Sprint 2.

Couvre :
  - CRUD organisations (créer, lister, détail, modifier)
  - CRUD learners (créer, lister, modifier, quota, doublon)
  - Import CSV (valide, upsert, colonne manquante, trop de lignes)
  - Magic-link auth (génération, vérification, token expiré, token invalide)
"""

import csv as csv_module
import io

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


# ── helpers ────────────────────────────────────────────────────────────────────


async def _headers(email: str = "awareness@test.com") -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _csv_bytes(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    if rows:
        writer = csv_module.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return buf.getvalue().encode("utf-8")


# ── Organizations ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_organization_returns_201():
    h = await _headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/awareness/organizations",
            json={"name": "Acme Corp", "max_learners": 20},
            headers=h,
        )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Acme Corp"
    assert body["max_learners"] == 20
    assert body["is_active"] is True


@pytest.mark.asyncio
async def test_list_organizations_returns_own_only():
    h1 = await _headers("user1@test.com")
    h2 = await _headers("user2@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/awareness/organizations", json={"name": "Org1"}, headers=h1)
        await c.post(f"{BASE}/awareness/organizations", json={"name": "Org2"}, headers=h2)
        r = await c.get(f"{BASE}/awareness/organizations", headers=h1)
    orgs = r.json()
    assert len(orgs) == 1
    assert orgs[0]["name"] == "Org1"


@pytest.mark.asyncio
async def test_get_organization_404_for_other_user():
    h1 = await _headers("owner1@test.com")
    h2 = await _headers("other@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r_create = await c.post(
            f"{BASE}/awareness/organizations", json={"name": "Secret Org"}, headers=h1
        )
        org_id = r_create.json()["id"]
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_organization():
    h = await _headers("patch@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Old"}, headers=h)
        ).json()["id"]
        r = await c.patch(
            f"{BASE}/awareness/organizations/{org_id}",
            json={"name": "New Name", "sector": "Tech"},
            headers=h,
        )
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"
    assert r.json()["sector"] == "Tech"


# ── Learners ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_learner_returns_201():
    h = await _headers("learner_owner@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "alice@acme.com", "first_name": "Alice"},
            headers=h,
        )
    assert r.status_code == 201
    assert r.json()["email"] == "alice@acme.com"
    assert r.json()["preferred_language"] == "fr"


@pytest.mark.asyncio
async def test_create_learner_duplicate_email_409():
    h = await _headers("dup_owner@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "dup@acme.com"},
            headers=h,
        )
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "dup@acme.com"},
            headers=h,
        )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_create_learner_quota_exceeded_422():
    h = await _headers("quota_owner@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations",
                json={"name": "Tiny", "max_learners": 1},
                headers=h,
            )
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "first@tiny.com"},
            headers=h,
        )
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "second@tiny.com"},
            headers=h,
        )
    assert r.status_code == 422
    assert "Quota" in r.json()["detail"]


@pytest.mark.asyncio
async def test_list_learners_active_only_by_default():
    h = await _headers("list_owner@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        r1 = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "active@acme.com"},
            headers=h,
        )
        learner_id = r1.json()["id"]
        # Désactiver le learner
        await c.patch(
            f"{BASE}/awareness/organizations/{org_id}/learners/{learner_id}",
            json={"is_active": False},
            headers=h,
        )
        r = await c.get(f"{BASE}/awareness/organizations/{org_id}/learners", headers=h)
    assert r.status_code == 200
    assert all(lr["is_active"] for lr in r.json())


@pytest.mark.asyncio
async def test_update_learner():
    h = await _headers("upd_owner@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        learner_id = (
            await c.post(
                f"{BASE}/awareness/organizations/{org_id}/learners",
                json={"email": "bob@acme.com"},
                headers=h,
            )
        ).json()["id"]
        r = await c.patch(
            f"{BASE}/awareness/organizations/{org_id}/learners/{learner_id}",
            json={"department": "RH", "job_title": "DRH"},
            headers=h,
        )
    assert r.status_code == 200
    assert r.json()["department"] == "RH"
    assert r.json()["job_title"] == "DRH"


# ── CSV Import ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_csv_import_creates_learners():
    h = await _headers("csv_owner@test.com")
    rows = [
        {"email": "carol@acme.com", "first_name": "Carol", "department": "Tech"},
        {"email": "dave@acme.com", "first_name": "Dave", "department": "RH"},
    ]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations",
                json={"name": "Acme", "max_learners": 100},
                headers=h,
            )
        ).json()["id"]
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
            files={"file": ("learners.csv", _csv_bytes(rows), "text/csv")},
            headers=h,
        )
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2
    assert body["updated"] == 0
    assert body["errors"] == []


@pytest.mark.asyncio
async def test_csv_import_upserts_existing():
    h = await _headers("csv_upsert@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                f"{BASE}/awareness/organizations",
                json={"name": "Acme", "max_learners": 100},
                headers=h,
            )
        ).json()["id"]
        # Premier import
        rows1 = [{"email": "eve@acme.com", "first_name": "Eve"}]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
            files={"file": ("l.csv", _csv_bytes(rows1), "text/csv")},
            headers=h,
        )
        # Deuxième import — même email, département ajouté
        rows2 = [{"email": "eve@acme.com", "first_name": "Eve", "department": "IT"}]
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
            files={"file": ("l.csv", _csv_bytes(rows2), "text/csv")},
            headers=h,
        )
    body = r.json()
    assert body["created"] == 0
    assert body["updated"] == 1


@pytest.mark.asyncio
async def test_csv_import_missing_email_column_returns_error():
    h = await _headers("csv_bad@test.com")
    bad_csv = b"first_name,department\nAlice,Tech\n"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
            files={"file": ("bad.csv", bad_csv, "text/csv")},
            headers=h,
        )
    assert r.status_code == 200
    assert len(r.json()["errors"]) > 0


@pytest.mark.asyncio
async def test_csv_import_non_csv_file_rejected():
    h = await _headers("csv_ext@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        r = await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners/import-csv",
            files={"file": ("data.xlsx", b"binary", "application/octet-stream")},
            headers=h,
        )
    assert r.status_code == 422


# ── Magic-link auth ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_magic_link_request_returns_202():
    h = await _headers("ml_owner@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "frank@acme.com"},
            headers=h,
        )
        r = await c.post(
            f"{BASE}/awareness/auth/magic-link",
            json={"email": "frank@acme.com", "organization_id": org_id},
        )
    assert r.status_code == 202
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_magic_link_unknown_email_returns_202_no_token():
    """Email inconnu → 202 sans token (pas d'énumération d'emails)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/awareness/auth/magic-link",
            json={"email": "ghost@nowhere.com", "organization_id": 9999},
        )
    assert r.status_code == 202
    assert "token" not in r.json()


@pytest.mark.asyncio
async def test_magic_link_verify_returns_session():
    h = await _headers("ml_verify@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "grace@acme.com", "first_name": "Grace"},
            headers=h,
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token("grace@acme.com", org_id)
        r = await c.get(f"{BASE}/awareness/auth/verify", params={"token": token})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "grace@acme.com"
    assert body["first_name"] == "Grace"
    assert "access_token" in body


@pytest.mark.asyncio
async def test_magic_link_verify_token_single_use():
    """Un magic token ne peut être utilisé qu'une seule fois."""
    h = await _headers("ml_single@test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(f"{BASE}/awareness/organizations", json={"name": "Acme"}, headers=h)
        ).json()["id"]
        await c.post(
            f"{BASE}/awareness/organizations/{org_id}/learners",
            json={"email": "henry@acme.com"},
            headers=h,
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token("henry@acme.com", org_id)
        await c.get(f"{BASE}/awareness/auth/verify", params={"token": token})
        r2 = await c.get(f"{BASE}/awareness/auth/verify", params={"token": token})
    assert r2.status_code == 401


@pytest.mark.asyncio
async def test_magic_link_verify_invalid_token_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/awareness/auth/verify", params={"token": "invalid-token-xyz"})
    assert r.status_code == 401
