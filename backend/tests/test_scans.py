"""
Integration tests — /api/v1/scans
Covers: trigger (202), frequency enforcement (429), list (pagination),
        get by ID, auth isolation, CSV export, PDF 404.
"""

import pytest
from datetime import datetime, timedelta, timezone
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _site(client: AsyncClient, headers: dict, url: str = "https://example.com") -> int:
    with patch("app.api.v1.endpoints.sites.get_active_plan", new=AsyncMock(return_value=MagicMock(max_sites=5))):
        r = await client.post(f"{BASE}/sites", json={"url": url, "name": "Test"}, headers=headers)
    return r.json()["id"]


@pytest.mark.asyncio
async def test_trigger_scan_returns_202():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "scan1@test.com")
            site_id = await _site(c, h)
            r = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)
    assert r.status_code == 202
    assert "scan_id" in r.json()


@pytest.mark.asyncio
async def test_trigger_scan_unknown_site_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "scan2@test.com")
        r = await c.post(f"{BASE}/scans/trigger/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_trigger_scan_other_user_site_returns_404():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner3@test.com")
            site_id = await _site(c, h1)

            h2 = await _headers(c, "hacker@test.com")
            r = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_scan_frequency_enforcement_429():
    """Second scan within the interval window must return 429."""
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "freq@test.com")
            site_id = await _site(c, h)

            # First scan — create a "done" scan with finished_at = now
            scan_r = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)
            scan_id = scan_r.json()["scan_id"]

            # Manually set it to "done" via DB (patch the query result)
            from app.core.database import AsyncSessionLocal
            from app.models.scan import Scan
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Scan).where(Scan.id == scan_id))
                scan = result.scalar_one()
                scan.status = "done"
                scan.finished_at = datetime.now(timezone.utc)
                await db.commit()

            # Second trigger — should be blocked (interval_days=30 default, 0 days elapsed)
            r2 = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)

    assert r2.status_code == 429
    assert "Scan trop récent" in r2.json()["detail"]


@pytest.mark.asyncio
async def test_list_scans_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "list1@test.com")
        site_id = await _site(c, h)
        r = await c.get(f"{BASE}/scans/site/{site_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 0
    assert r.json()["items"] == []


@pytest.mark.asyncio
async def test_list_scans_after_trigger():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "list2@test.com")
            site_id = await _site(c, h)
            await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)

            r = await c.get(f"{BASE}/scans/site/{site_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_scans_pagination():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "page@test.com")
            site_id = await _site(c, h)
            await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)

            r = await c.get(f"{BASE}/scans/site/{site_id}?page=1&per_page=5", headers=h)
    data = r.json()
    assert data["page"] == 1
    assert data["per_page"] == 5
    assert data["pages"] >= 1


@pytest.mark.asyncio
async def test_get_scan_returns_correct_scan():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "get1@test.com")
            site_id = await _site(c, h)
            trig = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)
            scan_id = trig.json()["scan_id"]

            r = await c.get(f"{BASE}/scans/{scan_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == scan_id


@pytest.mark.asyncio
async def test_get_scan_other_user_returns_404():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner4@test.com")
            site_id = await _site(c, h1)
            trig = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h1)
            scan_id = trig.json()["scan_id"]

            h2 = await _headers(c, "spy2@test.com")
            r = await c.get(f"{BASE}/scans/{scan_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_pdf_not_ready_returns_404():
    with patch("app.services.scan_service.run_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "pdf@test.com")
            site_id = await _site(c, h)
            trig = await c.post(f"{BASE}/scans/trigger/{site_id}", headers=h)
            scan_id = trig.json()["scan_id"]

            r = await c.get(f"{BASE}/scans/{scan_id}/pdf", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_csv_export_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/scans/site/1/export")
    # HTTPBearer raises 403 when no Authorization header is provided
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_csv_export_unknown_site_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "csv@test.com")
        r = await c.get(f"{BASE}/scans/site/99999/export", headers=h)
    assert r.status_code == 404
