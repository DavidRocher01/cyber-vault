"""
Integration tests — /api/v1/admin/scans
Covers: auth guard, empty list, list with data, required fields, limit param.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.public_scan import PublicScan

BASE = "/api/v1"


def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    return patch("app.core.deps.settings", mock)


async def _seed_scan(target_url: str, status: str = "completed", overall_status: str | None = "safe") -> None:
    import app.core.database as _db
    async with _db.AsyncSessionLocal() as db:
        scan = PublicScan(
            target_url=target_url,
            status=status,
            overall_status=overall_status,
            created_at=datetime.now(timezone.utc),
        )
        db.add(scan)
        await db.commit()


# ── Auth guard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_scans_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_scans_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── List scans ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_scans_valid_key_returns_200():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_scans_empty_db_returns_empty_list():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "test-secret-key"})
    assert r.json() == []


@pytest.mark.asyncio
async def test_admin_scans_shows_seeded_scan():
    await _seed_scan("https://example.com")
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "test-secret-key"})
    scans = r.json()
    assert len(scans) == 1
    assert scans[0]["target_url"] == "https://example.com"
    assert scans[0]["status"] == "completed"
    assert scans[0]["overall_status"] == "safe"


@pytest.mark.asyncio
async def test_admin_scans_response_has_required_fields():
    await _seed_scan("https://fields-test.com")
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "test-secret-key"})
    scan = r.json()[0]
    for key in ("id", "target_url", "status", "overall_status", "created_at", "finished_at", "error_message"):
        assert key in scan, f"Missing key: {key}"


@pytest.mark.asyncio
async def test_admin_scans_failed_scan_has_no_overall_status():
    await _seed_scan("https://failed.com", status="failed", overall_status=None)
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "test-secret-key"})
    scan = r.json()[0]
    assert scan["status"] == "failed"
    assert scan["overall_status"] is None


@pytest.mark.asyncio
async def test_admin_scans_limit_parameter():
    for i in range(5):
        await _seed_scan(f"https://site{i}.com")
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans?limit=3", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    assert len(r.json()) == 3


@pytest.mark.asyncio
async def test_admin_scans_ordered_by_created_at_desc():
    await _seed_scan("https://older.com", status="completed")
    await _seed_scan("https://newer.com", status="pending", overall_status=None)
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/scans", headers={"x-admin-key": "test-secret-key"})
    scans = r.json()
    assert scans[0]["target_url"] == "https://newer.com"
    assert scans[1]["target_url"] == "https://older.com"
