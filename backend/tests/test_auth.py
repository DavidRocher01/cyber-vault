"""Auth endpoint tests — backed by the in-memory SQLite DB from conftest."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(http_client: AsyncClient):
    r = await http_client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "StrongPass123!",
    })
    assert r.status_code == 201
    assert r.json()["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(http_client: AsyncClient):
    payload = {"email": "dup@example.com", "password": "StrongPass123!"}
    await http_client.post("/api/v1/auth/register", json=payload)
    r = await http_client.post("/api/v1/auth/register", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_login_success(http_client: AsyncClient):
    await http_client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "StrongPass123!",
    })
    r = await http_client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "StrongPass123!",
    })
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" not in r.json()
    assert "refresh_token" in r.cookies


@pytest.mark.asyncio
async def test_login_invalid_credentials(http_client: AsyncClient):
    r = await http_client.post("/api/v1/auth/login", json={
        "email": "ghost@example.com",
        "password": "wrong",
    })
    assert r.status_code == 401
