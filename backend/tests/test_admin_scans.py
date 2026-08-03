"""
Integration tests — /api/v1/admin/scans
Covers: auth guard, empty list, list with data, required fields, limit param.
"""

from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.public_scan import PublicScan

BASE = "/api/v1"


async def _seed_scan(
    target_url: str, status: str = "completed", overall_status: str | None = "safe"
) -> None:
    import app.core.database as _db

    async with _db.AsyncSessionLocal() as db:
        scan = PublicScan(
            target_url=target_url,
            status=status,
            overall_status=overall_status,
            created_at=datetime.now(UTC),
        )
        db.add(scan)
        await db.commit()


# ── Auth guard ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_admin_scans_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_scans_wrong_key_returns_403(entetes_non_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_non_admin)
    assert r.status_code == 403


# ── List scans ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_scans_valid_key_returns_200(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_admin)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_scans_empty_db_returns_empty_list(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_admin)
    assert r.json() == []


@pytest.mark.asyncio
async def test_admin_scans_shows_seeded_scan(entetes_admin):
    await _seed_scan("https://example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_admin)
    scans = r.json()
    assert len(scans) == 1
    assert scans[0]["target_url"] == "https://example.com"
    assert scans[0]["status"] == "completed"
    assert scans[0]["overall_status"] == "safe"


@pytest.mark.asyncio
async def test_admin_scans_response_has_required_fields(entetes_admin):
    await _seed_scan("https://fields-test.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_admin)
    scan = r.json()[0]
    for key in (
        "id",
        "target_url",
        "status",
        "overall_status",
        "created_at",
        "finished_at",
        "error_message",
    ):
        assert key in scan, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_admin_scans_failed_scan_has_no_overall_status(entetes_admin):
    await _seed_scan("https://failed.com", status="failed", overall_status=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_admin)
    scan = r.json()[0]
    assert scan["status"] == "failed"
    assert scan["overall_status"] is None


@pytest.mark.asyncio
async def test_admin_scans_limit_parameter(entetes_admin):
    for i in range(5):
        await _seed_scan(f"https://site{i}.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/admin/scans?limit=3",
            headers=entetes_admin,
        )
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_admin_scans_ordered_by_created_at_desc(entetes_admin):
    await _seed_scan("https://older.com", status="completed")
    await _seed_scan("https://newer.com", status="pending", overall_status=None)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/scans", headers=entetes_admin)
    scans = r.json()
    assert scans[0]["target_url"] == "https://newer.com"
    assert scans[1]["target_url"] == "https://older.com"
