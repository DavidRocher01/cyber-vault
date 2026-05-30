"""
Integration tests — /api/v1/rssi (Sprint 1)
Covers: client CRUD (enhanced schema), visits CRUD, actions CRUD, auth guards.
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

BASE = "/api/v1"


# ── helpers ────────────────────────────────────────────────────────────────────


async def _register_and_login(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(
        f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"}
    )
    r = await http_client.post(
        f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _register_and_login_consultant(http_client: AsyncClient, email: str) -> dict:
    import app.core.database as _db_mod
    from app.models.user import User

    headers = await _register_and_login(http_client, email)
    async with _db_mod.AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers


async def _create_client(
    http_client: AsyncClient, headers: dict, name: str = "Acme", **kwargs
) -> dict:
    payload = {"name": name, **kwargs}
    r = await http_client.post(f"{BASE}/rssi/clients", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_clients_no_auth_returns_401(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients")
    assert r.status_code == 401


# ── Client CRUD ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_client_basic(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi1@test.com")
    client = await _create_client(http_client, headers)
    assert client["name"] == "Acme"
    assert client["status"] == "active"
    assert client["formula"] is None
    assert client["sites_count"] == 0


@pytest.mark.asyncio
async def test_create_client_full_schema(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi2@test.com")
    client = await _create_client(
        http_client,
        headers,
        name="Corp SA",
        formula="premium",
        monthly_amount=3200.0,
        contract_renewal_at="2027-01-01",
    )
    assert client["formula"] == "premium"
    assert client["monthly_amount"] == 3200.0
    assert client["contract_renewal_at"] == "2027-01-01"


@pytest.mark.asyncio
async def test_create_client_invalid_formula_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi3@test.com")
    r = await http_client.post(
        f"{BASE}/rssi/clients",
        json={"name": "Corp", "formula": "ultra"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_list_clients_returns_own_clients_only(http_client: AsyncClient):
    h1 = await _register_and_login_consultant(http_client, "rssi4@test.com")
    h2 = await _register_and_login_consultant(http_client, "rssi5@test.com")

    await _create_client(http_client, h1, "Client user1")
    await _create_client(http_client, h1, "Client user1 bis")
    await _create_client(http_client, h2, "Client user2")

    r = await http_client.get(f"{BASE}/rssi/clients", headers=h1)
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "Client user1" in names
    assert "Client user1 bis" in names
    assert "Client user2" not in names


@pytest.mark.asyncio
async def test_update_client_status(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi6@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.put(
        f"{BASE}/rssi/clients/{cid}",
        json={"status": "churned"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "churned"


@pytest.mark.asyncio
async def test_update_client_invalid_status_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi7@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}",
        json={"status": "unknown"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_client(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi8@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.delete(f"{BASE}/rssi/clients/{cid}", headers=headers)
    assert r.status_code == 204

    r2 = await http_client.get(f"{BASE}/rssi/clients", headers=headers)
    assert all(c["id"] != cid for c in r2.json())


@pytest.mark.asyncio
async def test_cannot_access_other_user_client(http_client: AsyncClient):
    h1 = await _register_and_login_consultant(http_client, "rssi9@test.com")
    h2 = await _register_and_login_consultant(http_client, "rssi10@test.com")
    client = await _create_client(http_client, h1)

    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}",
        json={"name": "Hacked"},
        headers=h2,
    )
    assert r.status_code == 404


# ── Visits CRUD ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_visit(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi11@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "onsite",
        },
        headers=headers,
    )
    assert r.status_code == 201
    v = r.json()
    assert v["client_id"] == cid
    assert v["scheduled_date"] == "2026-06-15"
    assert v["visit_type"] == "monthly"
    assert v["status"] == "planned"


@pytest.mark.asyncio
async def test_list_visits(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi12@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    for d in ["2026-06-15", "2026-07-15"]:
        await http_client.post(
            f"{BASE}/rssi/clients/{cid}/visits",
            json={"scheduled_date": d, "visit_type": "monthly", "location": "remote"},
            headers=headers,
        )

    r = await http_client.get(f"{BASE}/rssi/clients/{cid}/visits", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 2


@pytest.mark.asyncio
async def test_update_visit_to_completed(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi13@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "onsite",
        },
        headers=headers,
    )
    vid = r.json()["id"]

    r2 = await http_client.put(
        f"{BASE}/rssi/clients/{cid}/visits/{vid}",
        json={
            "status": "completed",
            "actual_date": "2026-06-15",
            "duration_hours": 3.5,
        },
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"
    assert r2.json()["duration_hours"] == 3.5


@pytest.mark.asyncio
async def test_create_visit_invalid_type_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi14@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "surprise",
            "location": "onsite",
        },
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_visit(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi15@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "onsite",
        },
        headers=headers,
    )
    vid = r.json()["id"]

    r2 = await http_client.delete(f"{BASE}/rssi/clients/{cid}/visits/{vid}", headers=headers)
    assert r2.status_code == 204

    r3 = await http_client.get(f"{BASE}/rssi/clients/{cid}/visits", headers=headers)
    assert all(v["id"] != vid for v in r3.json())


# ── Actions CRUD ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_action(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi16@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/actions",
        json={
            "title": "Mettre en place MFA",
            "category": "technical",
            "priority": "high",
            "assigned_to": "client_it",
            "due_date": "2026-07-01",
        },
        headers=headers,
    )
    assert r.status_code == 201
    a = r.json()
    assert a["title"] == "Mettre en place MFA"
    assert a["priority"] == "high"
    assert a["status"] == "open"
    assert a["completed_at"] is None


@pytest.mark.asyncio
async def test_list_actions(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi17@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    for title in ["Action A", "Action B", "Action C"]:
        await http_client.post(
            f"{BASE}/rssi/clients/{cid}/actions",
            json={"title": title, "priority": "medium"},
            headers=headers,
        )

    r = await http_client.get(f"{BASE}/rssi/clients/{cid}/actions", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_filter_actions_by_status(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi18@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r1 = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/actions",
        json={"title": "Open action", "priority": "medium"},
        headers=headers,
    )
    aid = r1.json()["id"]
    await http_client.post(
        f"{BASE}/rssi/clients/{cid}/actions",
        json={"title": "Another open", "priority": "low"},
        headers=headers,
    )

    # Close one action
    await http_client.put(
        f"{BASE}/rssi/clients/{cid}/actions/{aid}",
        json={"status": "done"},
        headers=headers,
    )

    r_done = await http_client.get(
        f"{BASE}/rssi/clients/{cid}/actions?status_filter=done", headers=headers
    )
    assert r_done.status_code == 200
    assert len(r_done.json()) == 1

    r_open = await http_client.get(
        f"{BASE}/rssi/clients/{cid}/actions?status_filter=open", headers=headers
    )
    assert len(r_open.json()) == 1


@pytest.mark.asyncio
async def test_update_action_to_done_sets_completed_at(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi19@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/actions",
        json={"title": "Fix SSL cert", "priority": "critical"},
        headers=headers,
    )
    aid = r.json()["id"]

    r2 = await http_client.put(
        f"{BASE}/rssi/clients/{cid}/actions/{aid}",
        json={"status": "done"},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "done"
    assert r2.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_create_action_invalid_priority_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi20@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/actions",
        json={"title": "Test", "priority": "ultra-critical"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delete_action(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi21@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]

    r = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/actions",
        json={"title": "To delete", "priority": "low"},
        headers=headers,
    )
    aid = r.json()["id"]

    r2 = await http_client.delete(f"{BASE}/rssi/clients/{cid}/actions/{aid}", headers=headers)
    assert r2.status_code == 204

    r3 = await http_client.get(f"{BASE}/rssi/clients/{cid}/actions", headers=headers)
    assert all(a["id"] != aid for a in r3.json())


@pytest.mark.asyncio
async def test_action_not_accessible_from_other_client(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi22@test.com")
    c1 = await _create_client(http_client, headers, "Client 1")
    c2 = await _create_client(http_client, headers, "Client 2")

    r = await http_client.post(
        f"{BASE}/rssi/clients/{c1['id']}/actions",
        json={"title": "Private action", "priority": "medium"},
        headers=headers,
    )
    aid = r.json()["id"]

    # Access via wrong client
    r2 = await http_client.get(
        f"{BASE}/rssi/clients/{c2['id']}/actions",
        headers=headers,
    )
    assert all(a["id"] != aid for a in r2.json())


# ── get_rssi_consultant dependency ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_rssi_consultant_raises_for_normal_user(http_client: AsyncClient):
    """get_rssi_consultant should 403 if is_rssi_consultant=False."""
    from unittest.mock import MagicMock

    from fastapi import HTTPException

    from app.core.deps import get_rssi_consultant
    from app.models.user import User

    user = MagicMock(spec=User)
    user.is_rssi_consultant = False

    with pytest.raises(HTTPException) as exc:
        await get_rssi_consultant(current_user=user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_get_rssi_consultant_passes_for_rssi_user(http_client: AsyncClient):
    from unittest.mock import MagicMock

    from app.core.deps import get_rssi_consultant
    from app.models.user import User

    user = MagicMock(spec=User)
    user.is_rssi_consultant = True

    result = await get_rssi_consultant(current_user=user)
    assert result is user


# ── list_clients — site/scan aggregation ──────────────────────────────────────


@pytest.mark.asyncio
async def test_list_clients_aggregates_site_and_scan_status(
    http_client: AsyncClient, db_session: AsyncSession
):
    """Covers the site/scan join branches in list_clients (lines 221, 226-233, 242-244)."""
    from app.models.scan import Scan
    from app.models.site import Site
    from app.models.user import User

    headers = await _register_and_login_consultant(http_client, "rssi_sites@test.com")
    client = await _create_client(http_client, headers, "SiteCo")

    # Resolve the user and client objects directly from the test DB
    user_row = await db_session.execute(select(User).where(User.email == "rssi_sites@test.com"))
    user = user_row.scalar_one()

    site = Site(
        user_id=user.id,
        url="https://siteco.example.com",
        name="SiteCo Site",
        rssi_client_id=client["id"],
        is_active=True,
    )
    db_session.add(site)
    await db_session.flush()

    scan = Scan(
        site_id=site.id,
        status="done",
        overall_status="WARNING",
        finished_at=datetime.now(UTC),
    )
    db_session.add(scan)
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients", headers=headers)
    assert r.status_code == 200
    found = next((c for c in r.json() if c["id"] == client["id"]), None)
    assert found is not None
    assert found["sites_count"] == 1
    assert found["worst_status"] == "WARNING"
    assert found["last_scan_at"] is not None


# ── GET /clients/{id} ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_client_returns_own_client(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_getone@test.com")
    client = await _create_client(
        http_client, headers, "GetMe", formula="premium", monthly_amount=1500.0
    )
    r = await http_client.get(f"{BASE}/rssi/clients/{client['id']}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == client["id"]
    assert data["name"] == "GetMe"
    assert data["formula"] == "premium"


@pytest.mark.asyncio
async def test_get_client_404_for_unknown(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_getone_404@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999", headers=headers)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_client_404_for_other_user_client(http_client: AsyncClient):
    h1 = await _register_and_login_consultant(http_client, "rssi_getone_owner@test.com")
    h2 = await _register_and_login_consultant(http_client, "rssi_getone_spy@test.com")
    client = await _create_client(http_client, h1, "PrivateCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{client['id']}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_client_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/1")
    assert r.status_code == 401


# ── update_client — remaining branches ────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_client_invalid_formula_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_upd_formula@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}",
        json={"formula": "ultra"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_client_all_optional_fields(http_client: AsyncClient):
    """Covers update branches for email, formula, monthly_amount, dates, integrations."""
    headers = await _register_and_login_consultant(http_client, "rssi_upd_all@test.com")
    client = await _create_client(http_client, headers, "UpdateMe")
    cid = client["id"]

    r = await http_client.put(
        f"{BASE}/rssi/clients/{cid}",
        json={
            "email": "contact@updateme.com",
            "description": "Desc updated",
            "formula": "excellence",
            "monthly_amount": 4500.0,
            "contract_start_date": "2025-01-01",
            "contract_renewal_at": "2026-01-01",
            "notion_workspace_url": "https://notion.so/workspace",
            "pipedrive_deal_id": "deal-42",
            "pennylane_customer_id": "cust-99",
        },
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "contact@updateme.com"
    assert data["formula"] == "excellence"
    assert data["monthly_amount"] == 4500.0
    assert data["notion_workspace_url"] == "https://notion.so/workspace"
    assert data["pipedrive_deal_id"] == "deal-42"
    assert data["pennylane_customer_id"] == "cust-99"


# ── Visits — remaining branches ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_visit_invalid_location_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_visit_loc@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "helicopter",
        },
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_visit_not_found_returns_404(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_visit_404upd@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}/visits/99999",
        json={"status": "completed"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_visit_invalid_status_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_visit_badstatus@test.com")
    client = await _create_client(http_client, headers)
    r_v = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "onsite",
        },
        headers=headers,
    )
    vid = r_v.json()["id"]
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}/visits/{vid}",
        json={"status": "maybe"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_visit_invalid_type_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_visit_badtype@test.com")
    client = await _create_client(http_client, headers)
    r_v = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "onsite",
        },
        headers=headers,
    )
    vid = r_v.json()["id"]
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}/visits/{vid}",
        json={"visit_type": "surprise"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_visit_partial_fields(http_client: AsyncClient):
    """Covers scheduled_date, visit_type, location, notes update branches."""
    headers = await _register_and_login_consultant(http_client, "rssi_visit_partial@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]
    r_v = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/visits",
        json={
            "scheduled_date": "2026-06-15",
            "visit_type": "monthly",
            "location": "onsite",
        },
        headers=headers,
    )
    vid = r_v.json()["id"]

    r = await http_client.put(
        f"{BASE}/rssi/clients/{cid}/visits/{vid}",
        json={
            "scheduled_date": "2026-07-10",
            "visit_type": "quarterly",
            "location": "remote",
            "notes": "Reprogrammée",
        },
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["scheduled_date"] == "2026-07-10"
    assert data["visit_type"] == "quarterly"
    assert data["location"] == "remote"
    assert data["notes"] == "Reprogrammée"


@pytest.mark.asyncio
async def test_delete_visit_not_found_returns_404(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_visit_404del@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.delete(
        f"{BASE}/rssi/clients/{client['id']}/visits/99999",
        headers=headers,
    )
    assert r.status_code == 404


# ── Actions — remaining branches ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_action_empty_title_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_action_empty@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/actions",
        json={"title": "   ", "priority": "medium"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_action_not_found_returns_404(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_action_404upd@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}/actions/99999",
        json={"title": "Ghost"},
        headers=headers,
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_update_action_invalid_priority_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_action_badprio@test.com")
    client = await _create_client(http_client, headers)
    r_a = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/actions",
        json={"title": "Test", "priority": "medium"},
        headers=headers,
    )
    aid = r_a.json()["id"]
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}/actions/{aid}",
        json={"priority": "nuclear"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_action_invalid_status_returns_422(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_action_badstatus@test.com")
    client = await _create_client(http_client, headers)
    r_a = await http_client.post(
        f"{BASE}/rssi/clients/{client['id']}/actions",
        json={"title": "Test", "priority": "medium"},
        headers=headers,
    )
    aid = r_a.json()["id"]
    r = await http_client.put(
        f"{BASE}/rssi/clients/{client['id']}/actions/{aid}",
        json={"status": "maybe"},
        headers=headers,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_action_all_optional_fields(http_client: AsyncClient):
    """Covers title, description, category, priority, assigned_to, due_date, completed_at update branches."""
    headers = await _register_and_login_consultant(http_client, "rssi_action_allfields@test.com")
    client = await _create_client(http_client, headers)
    cid = client["id"]
    r_a = await http_client.post(
        f"{BASE}/rssi/clients/{cid}/actions",
        json={"title": "Initial", "priority": "low"},
        headers=headers,
    )
    aid = r_a.json()["id"]

    r = await http_client.put(
        f"{BASE}/rssi/clients/{cid}/actions/{aid}",
        json={
            "title": "Updated title",
            "description": "New description",
            "category": "governance",
            "priority": "high",
            "status": "in_progress",
            "assigned_to": "ciso@client.com",
            "due_date": "2026-09-01",
            "completed_at": "2026-08-01T10:00:00",
        },
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["title"] == "Updated title"
    assert data["description"] == "New description"
    assert data["category"] == "governance"
    assert data["priority"] == "high"
    assert data["status"] == "in_progress"
    assert data["assigned_to"] == "ciso@client.com"
    assert data["due_date"] == "2026-09-01"


@pytest.mark.asyncio
async def test_delete_action_not_found_returns_404(http_client: AsyncClient):
    headers = await _register_and_login_consultant(http_client, "rssi_action_404del@test.com")
    client = await _create_client(http_client, headers)
    r = await http_client.delete(
        f"{BASE}/rssi/clients/{client['id']}/actions/99999",
        headers=headers,
    )
    assert r.status_code == 404
