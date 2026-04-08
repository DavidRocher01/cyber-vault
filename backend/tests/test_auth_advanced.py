"""
Integration tests — auth advanced flows
Covers: account lockout, refresh token, logout, password validation,
        /users/me endpoint, weak password rejection.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


@pytest.mark.asyncio
async def test_weak_password_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={"email": "weak@test.com", "password": "123"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_invalid_email_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/register", json={"email": "not-an-email", "password": "StrongPass123!"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_account_lockout_after_5_failures():
    """After 5 wrong passwords the account must be locked (423)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "lock@test.com", "password": "StrongPass123!"})
        for _ in range(5):
            await c.post(f"{BASE}/auth/login", json={"email": "lock@test.com", "password": "wrong"})
        r = await c.post(f"{BASE}/auth/login", json={"email": "lock@test.com", "password": "StrongPass123!"})
    assert r.status_code == 429


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "u@test.com", "password": "StrongPass123!"})
        r = await c.post(f"{BASE}/auth/login", json={"email": "u@test.com", "password": "wrong"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/login", json={"email": "ghost@test.com", "password": "any"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_returns_new_access_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "rt@test.com", "password": "StrongPass123!"})
        login = await c.post(f"{BASE}/auth/login", json={"email": "rt@test.com", "password": "StrongPass123!"})
        refresh_token = login.json()["refresh_token"]

        r = await c.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_refresh_invalid_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/refresh", json={"refresh_token": "invalid-token"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_logout_invalidates_refresh_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "lo@test.com", "password": "StrongPass123!"})
        login = await c.post(f"{BASE}/auth/login", json={"email": "lo@test.com", "password": "StrongPass123!"})
        refresh_token = login.json()["refresh_token"]
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        await c.post(f"{BASE}/auth/logout", headers=headers, json={"refresh_token": refresh_token})

        r = await c.post(f"{BASE}/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_requires_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/users/me")
    # HTTPBearer returns 403 when no Authorization header is present
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_users_me_returns_current_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "me@test.com", "password": "StrongPass123!"})
        login = await c.post(f"{BASE}/auth/login", json={"email": "me@test.com", "password": "StrongPass123!"})
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        r = await c.get(f"{BASE}/users/me", headers=headers)
    assert r.status_code == 200
    assert r.json()["email"] == "me@test.com"


@pytest.mark.asyncio
async def test_bearer_token_malformed_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/users/me", headers={"Authorization": "Bearer garbage.token.here"})
    assert r.status_code == 401
