"""
Integration tests — /api/v1/url-scans
Covers: trigger (202), list (pagination), get by ID, delete,
        auth isolation, unauthenticated rejection.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── POST /url-scans ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_url_scan_returns_202():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urlscan1@test.com")
            r = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
    assert r.status_code == 202
    body = r.json()
    assert "id" in body
    assert body["status"] == "pending"
    assert body["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_trigger_url_scan_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_trigger_url_scan_invalid_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlscan_bad@test.com")
        r = await c.post(f"{BASE}/url-scans", json={"url": "not-a-url"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_trigger_url_scan_ftp_rejected_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlscan_ftp@test.com")
        r = await c.post(f"{BASE}/url-scans", json={"url": "ftp://files.example.com"}, headers=h)
    assert r.status_code == 422


# ── GET /url-scans ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_url_scans_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urllist1@test.com")
        r = await c.get(f"{BASE}/url-scans", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_list_url_scans_after_trigger():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urllist2@test.com")
            await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
            r = await c.get(f"{BASE}/url-scans", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1


@pytest.mark.asyncio
async def test_list_url_scans_pagination():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urlpage@test.com")
            for i in range(3):
                await c.post(f"{BASE}/url-scans", json={"url": f"https://example{i}.com"}, headers=h)
            r = await c.get(f"{BASE}/url-scans?page=1&per_page=2", headers=h)
    data = r.json()
    assert data["page"] == 1
    assert data["per_page"] == 2
    assert data["total"] == 3
    assert data["pages"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_url_scans_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/url-scans")
    assert r.status_code == 403


# ── GET /url-scans/{id} ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_url_scan_returns_correct_scan():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urlget1@test.com")
            created = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
            scan_id = created.json()["id"]
            r = await c.get(f"{BASE}/url-scans/{scan_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == scan_id


@pytest.mark.asyncio
async def test_get_url_scan_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urlget2@test.com")
        r = await c.get(f"{BASE}/url-scans/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_url_scan_other_user_returns_404():
    """User B cannot read user A's scan — auth isolation."""
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "urlowner@test.com")
            created = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h1)
            scan_id = created.json()["id"]

            h2 = await _headers(c, "urlspy@test.com")
            r = await c.get(f"{BASE}/url-scans/{scan_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_url_scan_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/url-scans/1")
    assert r.status_code == 403


# ── DELETE /url-scans/{id} ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_url_scan_returns_204():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urldel1@test.com")
            created = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
            scan_id = created.json()["id"]
            r = await c.delete(f"{BASE}/url-scans/{scan_id}", headers=h)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_url_scan_actually_removes_it():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "urldel2@test.com")
            created = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
            scan_id = created.json()["id"]
            await c.delete(f"{BASE}/url-scans/{scan_id}", headers=h)
            r = await c.get(f"{BASE}/url-scans/{scan_id}", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_url_scan_other_user_returns_404():
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "urldel_owner@test.com")
            created = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h1)
            scan_id = created.json()["id"]

            h2 = await _headers(c, "urldel_spy@test.com")
            r = await c.delete(f"{BASE}/url-scans/{scan_id}", headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_url_scan_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "urldel3@test.com")
        r = await c.delete(f"{BASE}/url-scans/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_url_scan_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.delete(f"{BASE}/url-scans/1")
    assert r.status_code == 403
