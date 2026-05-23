import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_register_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "StrongPass123!"
        })
    assert response.status_code == 201
    assert response.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        payload = {"email": "dup@example.com", "password": "StrongPass123!"}
        await client.post("/api/v1/auth/register", json=payload)
        response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/auth/register", json={
            "email": "login@example.com",
            "password": "StrongPass123!"
        })
        response = await client.post("/api/v1/auth/login", json={
            "email": "login@example.com",
            "password": "StrongPass123!"
        })
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()


@pytest.mark.asyncio
async def test_login_invalid_credentials():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/auth/login", json={
            "email": "ghost@example.com",
            "password": "wrong"
        })
    assert response.status_code == 401
