"""
Integration tests — /api/v1/code-scans
Covers: trigger git scan, upload zip, list, get, delete,
        auth isolation, input validation, pagination.
"""

import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_zip(filename: str = "main.py", content: str = "import os") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(filename, content)
    return buf.getvalue()


# ── Trigger (Git) ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_trigger_code_scan_returns_202():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "cs1@test.com")
            r = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h)
    assert r.status_code == 202
    assert "scan_id" in r.json()
    assert r.json()["scan_id"] > 0


@pytest.mark.asyncio
async def test_trigger_code_scan_without_token():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "cs2@test.com")
            r = await c.post(
                f"{BASE}/code-scans",
                json={"repo_url": "https://gitlab.com/org/project", "github_token": None},
                headers=h,
            )
    assert r.status_code == 202
    assert "scan_id" in r.json()


@pytest.mark.asyncio
async def test_trigger_code_scan_invalid_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "cs3@test.com")
        r = await c.post(f"{BASE}/code-scans", json={"repo_url": "not-a-url"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_trigger_code_scan_non_http_url_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "cs4@test.com")
        r = await c.post(f"{BASE}/code-scans", json={"repo_url": "git@github.com:user/repo.git"}, headers=h)
    assert r.status_code == 422
    assert "invalide" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_trigger_code_scan_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"})
    assert r.status_code == 403


# ── Upload ZIP ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_zip_returns_202():
    with patch("app.api.v1.endpoints.code_scans._run_zip_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "zip1@test.com")
            r = await c.post(
                f"{BASE}/code-scans/upload",
                files={"file": ("myapp.zip", _make_zip(), "application/zip")},
                headers=h,
            )
    assert r.status_code == 202
    assert "scan_id" in r.json()
    assert r.json()["scan_id"] > 0


@pytest.mark.asyncio
async def test_upload_non_zip_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "zip2@test.com")
        r = await c.post(
            f"{BASE}/code-scans/upload",
            files={"file": ("script.py", b"import os", "text/plain")},
            headers=h,
        )
    assert r.status_code == 422
    assert ".zip" in r.json()["detail"]


@pytest.mark.asyncio
async def test_upload_zip_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/code-scans/upload",
            files={"file": ("app.zip", _make_zip(), "application/zip")},
        )
    assert r.status_code == 403


# ── List ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_code_scans_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "list1@test.com")
        r = await c.get(f"{BASE}/code-scans", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_list_code_scans_after_trigger():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "list2@test.com")
            await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h)
            r = await c.get(f"{BASE}/code-scans", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["items"][0]["status"] == "pending"


@pytest.mark.asyncio
async def test_list_code_scans_pagination():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "list3@test.com")
            for i in range(3):
                await c.post(
                    f"{BASE}/code-scans",
                    json={"repo_url": f"https://github.com/user/repo{i}"},
                    headers=h,
                )
            r = await c.get(f"{BASE}/code-scans?page=1&per_page=2", headers=h)
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    assert data["pages"] == 2


@pytest.mark.asyncio
async def test_list_code_scans_isolation():
    """User A's scans must not be visible to User B."""
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner_cs@test.com")
            h2 = await _headers(c, "spy_cs@test.com")
            await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h1)
            r = await c.get(f"{BASE}/code-scans", headers=h2)
    assert r.json()["total"] == 0


# ── Get ───────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_code_scan_returns_correct_scan():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "get1@test.com")
            trig = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h)
            scan_id = trig.json()["scan_id"]
            r = await c.get(f"{BASE}/code-scans/{scan_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["id"] == scan_id
    assert r.json()["repo_url"] == "https://github.com/user/repo"


@pytest.mark.asyncio
async def test_get_code_scan_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "get2@test.com")
        r = await c.get(f"{BASE}/code-scans/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_get_code_scan_other_user_returns_404():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner_get@test.com")
            h2 = await _headers(c, "spy_get@test.com")
            trig = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h1)
            scan_id = trig.json()["scan_id"]
            r = await c.get(f"{BASE}/code-scans/{scan_id}", headers=h2)
    assert r.status_code == 404


# ── Delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_code_scan_returns_204():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "del1@test.com")
            trig = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h)
            scan_id = trig.json()["scan_id"]
            r = await c.delete(f"{BASE}/code-scans/{scan_id}", headers=h)
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_code_scan_removes_from_list():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "del2@test.com")
            trig = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h)
            scan_id = trig.json()["scan_id"]
            await c.delete(f"{BASE}/code-scans/{scan_id}", headers=h)
            r = await c.get(f"{BASE}/code-scans", headers=h)
    assert r.json()["total"] == 0


@pytest.mark.asyncio
async def test_delete_code_scan_unknown_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "del3@test.com")
        r = await c.delete(f"{BASE}/code-scans/99999", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_code_scan_other_user_returns_404():
    with patch("app.api.v1.endpoints.code_scans._run_background", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h1 = await _headers(c, "owner_del@test.com")
            h2 = await _headers(c, "spy_del@test.com")
            trig = await c.post(f"{BASE}/code-scans", json={"repo_url": "https://github.com/user/repo"}, headers=h1)
            scan_id = trig.json()["scan_id"]
            r = await c.delete(f"{BASE}/code-scans/{scan_id}", headers=h2)
    assert r.status_code == 404
