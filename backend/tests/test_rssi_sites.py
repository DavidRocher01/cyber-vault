"""
Integration tests — Sprint 5C
Covers:
  - GET /rssi/clients/{id}/sites (new endpoint)
  - GET /rssi/clients/{id} now returns real sites_count / worst_status / last_scan_at
"""
import pytest
from datetime import datetime, timezone
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.models.site import Site
from app.models.scan import Scan

BASE = "/api/v1"


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await http_client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Acme") -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _get_user_id(db_session: AsyncSession, email: str) -> int:
    row = await db_session.execute(select(User).where(User.email == email))
    return row.scalar_one().id


async def _insert_site(db_session: AsyncSession, user_id: int, client_id: int,
                       url: str = "https://example.com", name: str = "Test site",
                       is_active: bool = True) -> Site:
    site = Site(user_id=user_id, url=url, name=name,
                rssi_client_id=client_id, is_active=is_active)
    db_session.add(site)
    await db_session.flush()
    return site


async def _insert_scan(db_session: AsyncSession, site_id: int,
                       overall_status: str, finished_at: datetime | None = None) -> Scan:
    scan = Scan(
        site_id=site_id,
        status="done",
        overall_status=overall_status,
        finished_at=finished_at or datetime.now(timezone.utc),
    )
    db_session.add(scan)
    await db_session.flush()
    return scan


# ── Auth guard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sites_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/1/sites")
    assert r.status_code == 401


# ── 404 isolation ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sites_unknown_client(http_client: AsyncClient):
    h = await _auth(http_client, "sites_404@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999/sites", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_list_sites_cross_user_isolation(http_client: AsyncClient):
    h1 = await _auth(http_client, "sites_owner@test.com")
    h2 = await _auth(http_client, "sites_spy@test.com")
    c = await _create_client(http_client, h1, "OwnerCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h2)
    assert r.status_code == 404


# ── list_client_sites happy path ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sites_empty(http_client: AsyncClient):
    h = await _auth(http_client, "sites_empty@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_sites_returns_site_without_scan(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "sites_no_scan@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "NoScanCo")
    user_id = await _get_user_id(db_session, email)

    site = await _insert_site(db_session, user_id, c["id"], url="https://noscan.example.com")
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    assert r.status_code == 200
    sites = r.json()
    assert len(sites) == 1
    assert sites[0]["id"] == site.id
    assert sites[0]["url"] == "https://noscan.example.com"
    assert sites[0]["latest_scan_status"] is None
    assert sites[0]["last_scan_at"] is None


@pytest.mark.asyncio
async def test_list_sites_returns_scan_status(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "sites_with_scan@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "ScanCo")
    user_id = await _get_user_id(db_session, email)

    site = await _insert_site(db_session, user_id, c["id"])
    await _insert_scan(db_session, site.id, "CRITICAL")
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    assert r.status_code == 200
    assert r.json()[0]["latest_scan_status"] == "CRITICAL"


@pytest.mark.asyncio
async def test_list_sites_latest_scan_only(
    http_client: AsyncClient, db_session: AsyncSession
):
    """Only the most recent done scan's status is returned."""
    email = "sites_latest@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "LatestCo")
    user_id = await _get_user_id(db_session, email)

    site = await _insert_site(db_session, user_id, c["id"])
    older = datetime(2026, 1, 1, tzinfo=timezone.utc)
    newer = datetime(2026, 6, 1, tzinfo=timezone.utc)
    await _insert_scan(db_session, site.id, "WARNING", finished_at=older)
    await _insert_scan(db_session, site.id, "OK", finished_at=newer)
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    assert r.json()[0]["latest_scan_status"] == "OK"


@pytest.mark.asyncio
async def test_list_sites_excludes_inactive(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "sites_inactive@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "InactiveCo")
    user_id = await _get_user_id(db_session, email)

    await _insert_site(db_session, user_id, c["id"], url="https://active.example.com", is_active=True)
    await _insert_site(db_session, user_id, c["id"], url="https://inactive.example.com", is_active=False)
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["url"] == "https://active.example.com"


@pytest.mark.asyncio
async def test_list_sites_multiple(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "sites_multi@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "MultiCo")
    user_id = await _get_user_id(db_session, email)

    await _insert_site(db_session, user_id, c["id"], url="https://a.example.com", name="A")
    await _insert_site(db_session, user_id, c["id"], url="https://b.example.com", name="B")
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/sites", headers=h)
    assert r.status_code == 200
    assert len(r.json()) == 2


# ── GET /clients/{id} now returns real aggregates ─────────────────────────────

@pytest.mark.asyncio
async def test_get_client_sites_count_populated(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "gc_sites_count@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "AggCo")
    user_id = await _get_user_id(db_session, email)

    await _insert_site(db_session, user_id, c["id"])
    await _insert_site(db_session, user_id, c["id"], url="https://site2.example.com")
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}", headers=h)
    assert r.status_code == 200
    assert r.json()["sites_count"] == 2


@pytest.mark.asyncio
async def test_get_client_worst_status_populated(
    http_client: AsyncClient, db_session: AsyncSession
):
    email = "gc_worst@test.com"
    h = await _auth(http_client, email)
    c = await _create_client(http_client, h, "WorstCo")
    user_id = await _get_user_id(db_session, email)

    site1 = await _insert_site(db_session, user_id, c["id"], url="https://ok.example.com")
    site2 = await _insert_site(db_session, user_id, c["id"], url="https://critical.example.com")
    await _insert_scan(db_session, site1.id, "OK")
    await _insert_scan(db_session, site2.id, "CRITICAL")
    await db_session.commit()

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}", headers=h)
    assert r.json()["worst_status"] == "CRITICAL"


@pytest.mark.asyncio
async def test_get_client_no_sites_returns_null_aggregates(
    http_client: AsyncClient
):
    h = await _auth(http_client, "gc_no_sites@test.com")
    c = await _create_client(http_client, h, "EmptyAggCo")
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["sites_count"] == 0
    assert body["worst_status"] is None
    assert body["last_scan_at"] is None
