"""
Integration tests — GET /api/v1/rssi/clients/{id}/report (Sprint 5)
Covers: auth guard, 404 isolation, PDF content-type, non-empty body,
        report with actions/visits, report with empty client.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1"


async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await http_client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Acme", **kwargs) -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name, **kwargs}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_action(http_client: AsyncClient, headers: dict, client_id: int, **kwargs) -> dict:
    payload = {"title": "Test action", "priority": "medium", **kwargs}
    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/actions", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_visit(http_client: AsyncClient, headers: dict, client_id: int, date: str, **kwargs) -> dict:
    payload = {"scheduled_date": date, "visit_type": "monthly", "location": "onsite", **kwargs}
    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/visits", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Auth guard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/1/report")
    assert r.status_code == 401


# ── 404 isolation ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_404_unknown_client(http_client: AsyncClient):
    h = await _auth(http_client, "report_404@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999/report", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_report_404_other_user_client(http_client: AsyncClient):
    h1 = await _auth(http_client, "report_owner@test.com")
    h2 = await _auth(http_client, "report_spy@test.com")
    c = await _create_client(http_client, h1, "OwnerCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/report", headers=h2)
    assert r.status_code == 404


# ── PDF generation ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_report_returns_pdf_content_type(http_client: AsyncClient):
    h = await _auth(http_client, "report_ct@test.com")
    c = await _create_client(http_client, h, "PDFCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/report", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


@pytest.mark.asyncio
async def test_report_content_disposition_filename(http_client: AsyncClient):
    h = await _auth(http_client, "report_fname@test.com")
    c = await _create_client(http_client, h, "Acme Corp")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/report", headers=h)
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert ".pdf" in cd


@pytest.mark.asyncio
async def test_report_body_is_non_empty_pdf(http_client: AsyncClient):
    h = await _auth(http_client, "report_body@test.com")
    c = await _create_client(http_client, h, "BodyCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/report", headers=h)
    assert r.status_code == 200
    assert len(r.content) > 1000
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_report_with_full_client_data(http_client: AsyncClient):
    """Report generated for a client with formula, renewal, integrations."""
    h = await _auth(http_client, "report_full@test.com")
    c = await _create_client(
        http_client, h, "FullCo",
        formula="premium",
        monthly_amount=2500.0,
        contract_renewal_at="2027-06-01",
        notion_workspace_url="https://notion.so/ws",
        pipedrive_deal_id="deal-99",
        pennylane_customer_id="cust-42",
        description="Client prioritaire",
    )
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/report", headers=h)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_report_with_actions_and_visits(http_client: AsyncClient):
    """Report includes overdue action and completed visit — exercises full table rendering."""
    h = await _auth(http_client, "report_content@test.com")
    c = await _create_client(http_client, h, "ContentCo")
    cid = c["id"]

    await _create_action(http_client, h, cid, title="MFA obligatoire", priority="critical",
                         due_date="2025-01-01")
    await _create_action(http_client, h, cid, title="Patch serveur", priority="high",
                         due_date="2026-12-31")

    v = await _create_visit(http_client, h, cid, "2026-03-15", visit_type="quarterly", location="onsite")
    await http_client.put(
        f"{BASE}/rssi/clients/{cid}/visits/{v['id']}",
        json={"status": "completed", "actual_date": "2026-03-15", "duration_hours": 4.0},
        headers=h,
    )
    await _create_visit(http_client, h, cid, "2026-07-01")

    r = await http_client.get(f"{BASE}/rssi/clients/{cid}/report", headers=h)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
    assert len(r.content) > 2000


@pytest.mark.asyncio
async def test_report_empty_client_no_actions_no_visits(http_client: AsyncClient):
    """Report still generates without actions or visits."""
    h = await _auth(http_client, "report_empty@test.com")
    c = await _create_client(http_client, h, "EmptyCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/report", headers=h)
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
