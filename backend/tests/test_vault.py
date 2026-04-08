import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.vault_item import VaultItemCreate, VaultItemUpdate

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


def test_create_invalid_category_defaults_to_login():
    item = VaultItemCreate(title="Test", password_encrypted="enc", category="invalid_cat")
    assert item.category == "login"


def test_update_invalid_category_defaults_to_login():
    item = VaultItemUpdate(category="hacker")
    assert item.category == "login"


def test_update_valid_category_preserved():
    item = VaultItemUpdate(category="card")
    assert item.category == "card"


def test_create_with_category():
    item = VaultItemCreate(title="Netflix", password_encrypted="enc", category="login")
    assert item.category == "login"


@pytest.mark.asyncio
async def test_create_with_category_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(f"{BASE}/vault/", json={
            "title": "Card", "password_encrypted": "enc", "category": "card"
        }, headers=headers)
        assert r.status_code == 201
        assert r.json()["category"] == "card"


@pytest.mark.asyncio
async def test_update_category():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        headers = await _auth_headers(client)
        r = await client.post(f"{BASE}/vault/", json={
            "title": "Entry", "password_encrypted": "enc", "category": "login"
        }, headers=headers)
        item_id = r.json()["id"]

        r = await client.patch(f"{BASE}/vault/{item_id}", json={"category": "wifi"}, headers=headers)
        assert r.status_code == 200
        assert r.json()["category"] == "wifi"
