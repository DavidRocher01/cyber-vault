"""
Integration tests — /api/v1/nis2
Covers: GET /me (empty + with data), PUT /me (save, update, score, validation),
        GET /me/pdf, auth isolation, unauthenticated rejection.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── GET /nis2/me ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_assessment_empty_returns_default():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_get1@test.com")
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 0
    assert body["items"] == {}
    assert body["updated_at"] is None
    assert isinstance(body["categories"], list)
    assert len(body["categories"]) == 10  # 10 catégories NIS2


@pytest.mark.asyncio
async def test_get_assessment_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/nis2/me")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_get_assessment_categories_have_items():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_cats@test.com")
        r = await c.get(f"{BASE}/nis2/me", headers=h)
    categories = r.json()["categories"]
    total_items = sum(len(cat["items"]) for cat in categories)
    assert total_items == 34  # 34 critères NIS2


# ── PUT /nis2/me ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_save_assessment_returns_score():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_save1@test.com")
        payload = {"items": {"rssi": "compliant", "policy": "partial", "mgmt_training": "non_compliant"}}
        r = await c.put(f"{BASE}/nis2/me", json=payload, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] > 0
    assert body["items"]["rssi"] == "compliant"
    assert body["updated_at"] is not None


@pytest.mark.asyncio
async def test_save_assessment_score_100_when_all_compliant():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_score100@test.com")
        # Get all item IDs from the categories
        r_get = await c.get(f"{BASE}/nis2/me", headers=h)
        all_ids = [
            item["id"]
            for cat in r_get.json()["categories"]
            for item in cat["items"]
        ]
        payload = {"items": {item_id: "compliant" for item_id in all_ids}}
        r = await c.put(f"{BASE}/nis2/me", json=payload, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 100


@pytest.mark.asyncio
async def test_save_assessment_score_0_when_all_non_compliant():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_score0@test.com")
        r_get = await c.get(f"{BASE}/nis2/me", headers=h)
        all_ids = [
            item["id"]
            for cat in r_get.json()["categories"]
            for item in cat["items"]
        ]
        payload = {"items": {item_id: "non_compliant" for item_id in all_ids}}
        r = await c.put(f"{BASE}/nis2/me", json=payload, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 0


@pytest.mark.asyncio
async def test_save_assessment_na_excluded_from_score():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_na@test.com")
        # All NA → score should be 0 (no scorable items)
        r_get = await c.get(f"{BASE}/nis2/me", headers=h)
        all_ids = [
            item["id"]
            for cat in r_get.json()["categories"]
            for item in cat["items"]
        ]
        payload = {"items": {item_id: "na" for item_id in all_ids}}
        r = await c.put(f"{BASE}/nis2/me", json=payload, headers=h)
    assert r.status_code == 200
    assert r.json()["score"] == 0


@pytest.mark.asyncio
async def test_save_assessment_update_overwrites():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_update@test.com")
        await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "non_compliant"}}, headers=h)
        r = await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "compliant"}}, headers=h)
        r_get = await c.get(f"{BASE}/nis2/me", headers=h)
    assert r.status_code == 200
    assert r_get.json()["items"]["rssi"] == "compliant"


@pytest.mark.asyncio
async def test_save_assessment_invalid_item_id_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_badid@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={"items": {"unknown_item_xyz": "compliant"}}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_save_assessment_invalid_status_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_badstatus@test.com")
        r = await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "invalid_status"}}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_save_assessment_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "compliant"}})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_save_assessment_isolation_between_users():
    """User B cannot read or overwrite user A's assessment."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h1 = await _headers(c, "nis2_user_a@test.com")
        h2 = await _headers(c, "nis2_user_b@test.com")

        # User A saves
        await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "compliant"}}, headers=h1)

        # User B saves different data
        await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "non_compliant"}}, headers=h2)

        # User A's data is untouched
        r_a = await c.get(f"{BASE}/nis2/me", headers=h1)
    assert r_a.json()["items"]["rssi"] == "compliant"


# ── GET /nis2/me/pdf ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_pdf_returns_pdf_content_type():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_pdf1@test.com")
        r = await c.get(f"{BASE}/nis2/me/pdf", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["content-disposition"] == 'attachment; filename="cyberscan_nis2_conformite.pdf"'


@pytest.mark.asyncio
async def test_export_pdf_non_empty():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "nis2_pdf2@test.com")
        await c.put(f"{BASE}/nis2/me", json={"items": {"rssi": "compliant"}}, headers=h)
        r = await c.get(f"{BASE}/nis2/me/pdf", headers=h)
    assert len(r.content) > 1000  # PDF is never empty


@pytest.mark.asyncio
async def test_export_pdf_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/nis2/me/pdf")
    assert r.status_code == 403
