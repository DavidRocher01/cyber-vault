import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _auth_headers(client: AsyncClient) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": "vault@test.com", "password": "Pass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": "vault@test.com", "password": "Pass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_create_and_list_items():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(f"{BASE}/vault/", json={
            "title": "GitHub", "password_encrypted": "enc_secret", "username": "user"
        }, headers=headers)
        assert r.status_code == 201
        assert r.json()["title"] == "GitHub"

        r = await client.get(f"{BASE}/vault/", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) == 1


@pytest.mark.asyncio
async def test_update_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(f"{BASE}/vault/", json={
            "title": "Old Title", "password_encrypted": "enc"
        }, headers=headers)
        item_id = r.json()["id"]

        r = await client.patch(f"{BASE}/vault/{item_id}", json={"title": "New Title"}, headers=headers)
        assert r.status_code == 200
        assert r.json()["title"] == "New Title"


@pytest.mark.asyncio
async def test_delete_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(f"{BASE}/vault/", json={
            "title": "To Delete", "password_encrypted": "enc"
        }, headers=headers)
        item_id = r.json()["id"]

        r = await client.delete(f"{BASE}/vault/{item_id}", headers=headers)
        assert r.status_code == 204

        r = await client.get(f"{BASE}/vault/{item_id}", headers=headers)
        assert r.status_code == 404


@pytest.mark.asyncio
async def test_cannot_access_other_user_item():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        h1 = await _auth_headers(client)
        r = await client.post(f"{BASE}/vault/", json={
            "title": "Private", "password_encrypted": "enc"
        }, headers=h1)
        item_id = r.json()["id"]

        await client.post(f"{BASE}/auth/register", json={"email": "other@test.com", "password": "Pass123!"})
        r2 = await client.post(f"{BASE}/auth/login", json={"email": "other@test.com", "password": "Pass123!"})
        h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

        r = await client.get(f"{BASE}/vault/{item_id}", headers=h2)
        assert r.status_code == 404
