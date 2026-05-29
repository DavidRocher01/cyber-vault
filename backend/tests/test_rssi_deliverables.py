"""
Integration tests — /api/v1/rssi/clients/{id}/deliverables (Sprint 5A)
Covers: auth guard, 404 isolation, CRUD, validation, cross-user security.
"""

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(
        f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"}
    )
    r = await http_client.post(
        f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _auth_consultant(http_client, email: str) -> dict:
    """Register, login, and promote user to RSSI consultant for tests."""
    from sqlalchemy import select

    import app.core.database as _db_mod
    from app.models.user import User

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


async def _create_deliverable(
    http_client: AsyncClient, headers: dict, client_id: int, **kwargs
) -> dict:
    payload = {
        "title": "Compte-rendu de visite",
        "doc_type": "compte_rendu",
        "delivered_at": "2026-03-15",
        **kwargs,
    }
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client_id}/deliverables", json=payload, headers=headers
    )
    assert r.status_code == 201, r.text
    return r.json()


# ── Auth guards ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_deliverables_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/1/deliverables")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_deliverable_requires_auth(http_client: AsyncClient):
    r = await http_client.post(
        f"{BASE}/rssi/clients/1/deliverables",
        json={"title": "T", "delivered_at": "2026-01-01"},
    )
    assert r.status_code == 401


# ── 404 isolation ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_deliverables_unknown_client(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_list_404@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999/deliverables", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_deliverable_unknown_client(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_create_404@test.com")
    r = await http_client.post(
        f"{BASE}/rssi/clients/99999/deliverables",
        json={"title": "T", "delivered_at": "2026-01-01"},
        headers=h,
    )
    assert r.status_code == 404


# ── CRUD happy path ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_deliverable_minimal(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_minimal@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/deliverables",
        json={"title": "Rapport annuel", "delivered_at": "2026-06-01"},
        headers=h,
    )
    assert r.status_code == 201
    d = r.json()
    assert d["title"] == "Rapport annuel"
    assert d["doc_type"] == "autre"
    assert d["delivered_at"] == "2026-06-01"
    assert d["client_id"] == c["id"]
    assert d["file_url"] is None
    assert d["notes"] is None


@pytest.mark.asyncio
async def test_create_deliverable_full_fields(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_full@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/deliverables",
        json={
            "title": "Plan de remédiation Q1",
            "doc_type": "recommandation",
            "file_url": "https://notion.so/plan-q1",
            "notes": "Envoyé par email le 15/03",
            "delivered_at": "2026-03-15",
        },
        headers=h,
    )
    assert r.status_code == 201
    d = r.json()
    assert d["doc_type"] == "recommandation"
    assert d["file_url"] == "https://notion.so/plan-q1"
    assert d["notes"] == "Envoyé par email le 15/03"


@pytest.mark.asyncio
async def test_list_deliverables_empty(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_empty@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_deliverables_returns_multiple(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_multi@test.com")
    c = await _create_client(http_client, h)
    cid = c["id"]
    await _create_deliverable(http_client, h, cid, title="A", delivered_at="2026-01-01")
    await _create_deliverable(http_client, h, cid, title="B", delivered_at="2026-02-01")
    await _create_deliverable(http_client, h, cid, title="C", delivered_at="2026-03-01")
    r = await http_client.get(f"{BASE}/rssi/clients/{cid}/deliverables", headers=h)
    assert r.status_code == 200
    titles = [d["title"] for d in r.json()]
    assert set(titles) == {"A", "B", "C"}


@pytest.mark.asyncio
async def test_list_deliverables_ordered_by_date_desc(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_order@test.com")
    c = await _create_client(http_client, h)
    cid = c["id"]
    await _create_deliverable(http_client, h, cid, title="Early", delivered_at="2026-01-01")
    await _create_deliverable(http_client, h, cid, title="Late", delivered_at="2026-12-31")
    r = await http_client.get(f"{BASE}/rssi/clients/{cid}/deliverables", headers=h)
    dates = [d["delivered_at"] for d in r.json()]
    assert dates == sorted(dates, reverse=True)


@pytest.mark.asyncio
async def test_update_deliverable(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_update@test.com")
    c = await _create_client(http_client, h)
    d = await _create_deliverable(http_client, h, c["id"])
    r = await http_client.put(
        f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}",
        json={"title": "Titre modifié", "doc_type": "rapport", "notes": "Mis à jour"},
        headers=h,
    )
    assert r.status_code == 200
    upd = r.json()
    assert upd["title"] == "Titre modifié"
    assert upd["doc_type"] == "rapport"
    assert upd["notes"] == "Mis à jour"


@pytest.mark.asyncio
async def test_delete_deliverable(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_delete@test.com")
    c = await _create_client(http_client, h)
    d = await _create_deliverable(http_client, h, c["id"])
    r = await http_client.delete(f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}", headers=h)
    assert r.status_code == 204
    # confirm gone
    r2 = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables", headers=h)
    assert r2.json() == []


# ── Validation ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_deliverable_empty_title_returns_422(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_val_title@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/deliverables",
        json={"title": "   ", "delivered_at": "2026-01-01"},
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_create_deliverable_invalid_doc_type_returns_422(
    http_client: AsyncClient,
):
    h = await _auth_consultant(http_client, "deliv_val_type@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{c['id']}/deliverables",
        json={"title": "T", "doc_type": "invalid_type", "delivered_at": "2026-01-01"},
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_deliverable_invalid_doc_type_returns_422(
    http_client: AsyncClient,
):
    h = await _auth_consultant(http_client, "deliv_upd_val@test.com")
    c = await _create_client(http_client, h)
    d = await _create_deliverable(http_client, h, c["id"])
    r = await http_client.put(
        f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}",
        json={"doc_type": "bad_type"},
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_deliverable_not_found_returns_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_upd_404@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.put(
        f"{BASE}/rssi/clients/{c['id']}/deliverables/99999",
        json={"title": "X"},
        headers=h,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_deliverable_not_found_returns_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "deliv_del_404@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.delete(f"{BASE}/rssi/clients/{c['id']}/deliverables/99999", headers=h)
    assert r.status_code == 404


# ── Cross-user security ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_deliverables_cross_user_isolation(http_client: AsyncClient):
    h1 = await _auth_consultant(http_client, "deliv_iso_owner@test.com")
    h2 = await _auth_consultant(http_client, "deliv_iso_spy@test.com")
    c = await _create_client(http_client, h1, "IsolCo")
    await _create_deliverable(http_client, h1, c["id"])
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_deliverable_cross_user_isolation(http_client: AsyncClient):
    h1 = await _auth_consultant(http_client, "deliv_del_owner@test.com")
    h2 = await _auth_consultant(http_client, "deliv_del_spy@test.com")
    c = await _create_client(http_client, h1, "DelOwnerCo")
    d = await _create_deliverable(http_client, h1, c["id"])
    r = await http_client.delete(
        f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}", headers=h2
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_all_valid_doc_types(http_client: AsyncClient):
    """Each doc_type value is accepted."""
    h = await _auth_consultant(http_client, "deliv_doctypes@test.com")
    c = await _create_client(http_client, h, "TypesCo")
    for doc_type in ("compte_rendu", "rapport", "recommandation", "contrat", "autre"):
        r = await http_client.post(
            f"{BASE}/rssi/clients/{c['id']}/deliverables",
            json={
                "title": f"Doc {doc_type}",
                "doc_type": doc_type,
                "delivered_at": "2026-01-01",
            },
            headers=h,
        )
        assert r.status_code == 201, f"Failed for doc_type={doc_type}: {r.text}"
