"""Tests for deliverable file upload/download (P8)."""
import io
import pytest
from httpx import AsyncClient

BASE = "/api/v1"

# Minimal valid PDF bytes (1-byte body — enough for content-type + extension checks)
_PDF_BYTES = b"%PDF-1.4 fake content"
_DOCX_BYTES = b"PK fake docx content"


async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await http_client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

async def _auth_consultant(http_client, email: str) -> dict:
    """Register, login, and promote user to RSSI consultant for tests."""
    import app.core.database as _db_mod
    from sqlalchemy import select
    from app.models.user import User
    headers = await _auth(http_client, email)
    async with _db_mod.AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers




async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Upload Client") -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_deliverable(http_client: AsyncClient, headers: dict, client_id: int,
                               title: str = "Test livrable", file_key: str | None = None) -> dict:
    payload = {"title": title, "doc_type": "rapport", "delivered_at": "2026-05-01"}
    if file_key:
        payload["file_url"] = file_key
    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/deliverables", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Upload endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_requires_auth(http_client: AsyncClient):
    r = await http_client.post(f"{BASE}/rssi/clients/1/deliverables/upload",
                               files={"file": ("test.pdf", _PDF_BYTES, "application/pdf")})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_upload_unknown_client_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "upload_404@test.com")
    r = await http_client.post(f"{BASE}/rssi/clients/99999/deliverables/upload",
                               files={"file": ("test.pdf", _PDF_BYTES, "application/pdf")},
                               headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_cross_user_isolation(http_client: AsyncClient):
    h1 = await _auth_consultant(http_client, "upload_u1@test.com")
    h2 = await _auth_consultant(http_client, "upload_u2@test.com")
    c = await _create_client(http_client, h1)
    r = await http_client.post(f"{BASE}/rssi/clients/{c['id']}/deliverables/upload",
                               files={"file": ("test.pdf", _PDF_BYTES, "application/pdf")},
                               headers=h2)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_upload_pdf_success(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "upload_pdf@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(f"{BASE}/rssi/clients/{c['id']}/deliverables/upload",
                               files={"file": ("rapport.pdf", _PDF_BYTES, "application/pdf")},
                               headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "key" in data
    assert "filename" in data
    assert data["filename"] == "rapport.pdf"


@pytest.mark.asyncio
async def test_upload_returns_storage_key(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "upload_key@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(f"{BASE}/rssi/clients/{c['id']}/deliverables/upload",
                               files={"file": ("doc.pdf", _PDF_BYTES, "application/pdf")},
                               headers=h)
    key = r.json()["key"]
    # Local dev: key is a path starting with uploads/
    assert key  # non-empty


@pytest.mark.asyncio
async def test_upload_invalid_extension_rejected(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "upload_ext@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.post(f"{BASE}/rssi/clients/{c['id']}/deliverables/upload",
                               files={"file": ("script.exe", b"MZ executable", "application/octet-stream")},
                               headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_upload_too_large_rejected(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "upload_big@test.com")
    c = await _create_client(http_client, h)
    big = b"A" * (21 * 1024 * 1024)  # 21 MB
    r = await http_client.post(f"{BASE}/rssi/clients/{c['id']}/deliverables/upload",
                               files={"file": ("big.pdf", big, "application/pdf")},
                               headers=h)
    assert r.status_code == 422


# ── Download endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_download_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/clients/1/deliverables/1/download")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_download_unknown_client_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dl_404c@test.com")
    r = await http_client.get(f"{BASE}/rssi/clients/99999/deliverables/1/download", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_download_unknown_deliverable_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dl_404d@test.com")
    c = await _create_client(http_client, h)
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables/99999/download", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_download_no_file_404(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dl_nofile@test.com")
    c = await _create_client(http_client, h)
    d = await _create_deliverable(http_client, h, c["id"])  # no file_url
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}/download", headers=h)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_download_after_upload_returns_url(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dl_full@test.com")
    c = await _create_client(http_client, h)

    up = await http_client.post(f"{BASE}/rssi/clients/{c['id']}/deliverables/upload",
                                files={"file": ("rapport.pdf", _PDF_BYTES, "application/pdf")},
                                headers=h)
    key = up.json()["key"]

    d = await _create_deliverable(http_client, h, c["id"], file_key=key)

    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}/download", headers=h)
    assert r.status_code == 200
    assert "url" in r.json()
    assert r.json()["url"]  # non-empty URL


@pytest.mark.asyncio
async def test_download_cross_user_isolation(http_client: AsyncClient):
    h1 = await _auth_consultant(http_client, "dl_u1@test.com")
    h2 = await _auth_consultant(http_client, "dl_u2@test.com")
    c = await _create_client(http_client, h1)
    d = await _create_deliverable(http_client, h1, c["id"])
    r = await http_client.get(f"{BASE}/rssi/clients/{c['id']}/deliverables/{d['id']}/download", headers=h2)
    assert r.status_code == 404
