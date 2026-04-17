"""
Integration tests — forgot password & reset password flows.
Covers parcours #7 (demande reset), #8 (token valide), #9 (token expiré/invalide).
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


def _extract_token_from_mock(mock_send) -> str:
    """Extract the raw reset token from the URL passed to send_password_reset."""
    reset_url = mock_send.call_args[0][1]
    return reset_url.split("token=")[1]


# ── Forgot password ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_forgot_password_existing_email_returns_202():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "reset@test.com", "password": "StrongPass123!"})
        with patch("app.api.v1.endpoints.auth.send_password_reset"):
            r = await c.post(f"{BASE}/auth/forgot-password", json={"email": "reset@test.com"})
    assert r.status_code == 202


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_returns_202():
    """Toujours 202 pour éviter l'énumération des emails."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/forgot-password", json={"email": "ghost@test.com"})
    assert r.status_code == 202


@pytest.mark.asyncio
async def test_forgot_password_sends_email_for_valid_user():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "sendmail@test.com", "password": "StrongPass123!"})
        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "sendmail@test.com"})
    mock_send.assert_called_once()
    args = mock_send.call_args[0]
    assert args[0] == "sendmail@test.com"
    assert "reset-password" in args[1]


@pytest.mark.asyncio
async def test_forgot_password_does_not_send_email_for_unknown():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "nobody@test.com"})
    mock_send.assert_not_called()


# ── Reset password ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reset_password_valid_token_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "r1@test.com", "password": "StrongPass123!"})

        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "r1@test.com"})

        raw_token = _extract_token_from_mock(mock_send)

        r = await c.post(f"{BASE}/auth/reset-password", json={
            "token": raw_token,
            "password": "NewStrongPass456!",
        })
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_reset_password_allows_login_with_new_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "r2@test.com", "password": "StrongPass123!"})

        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "r2@test.com"})

        raw_token = _extract_token_from_mock(mock_send)

        await c.post(f"{BASE}/auth/reset-password", json={
            "token": raw_token,
            "password": "NewStrongPass456!",
        })

        login = await c.post(f"{BASE}/auth/login", json={"email": "r2@test.com", "password": "NewStrongPass456!"})
    assert login.status_code == 200
    assert "access_token" in login.json()


@pytest.mark.asyncio
async def test_reset_password_old_password_no_longer_works():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "r3@test.com", "password": "StrongPass123!"})

        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "r3@test.com"})

        raw_token = _extract_token_from_mock(mock_send)

        await c.post(f"{BASE}/auth/reset-password", json={
            "token": raw_token,
            "password": "NewStrongPass456!",
        })

        old_login = await c.post(f"{BASE}/auth/login", json={"email": "r3@test.com", "password": "StrongPass123!"})
    assert old_login.status_code == 401


@pytest.mark.asyncio
async def test_reset_password_invalid_token_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/auth/reset-password", json={
            "token": "completely-invalid-token",
            "password": "NewStrongPass456!",
        })
    assert r.status_code == 400
    assert "invalide" in r.json()["detail"].lower() or "expiré" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_reset_password_used_token_returns_400():
    """Un token déjà utilisé doit être rejeté (pas de double-reset)."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "r4@test.com", "password": "StrongPass123!"})

        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "r4@test.com"})

        raw_token = _extract_token_from_mock(mock_send)

        await c.post(f"{BASE}/auth/reset-password", json={"token": raw_token, "password": "NewPass456!"})
        r2 = await c.post(f"{BASE}/auth/reset-password", json={"token": raw_token, "password": "AnotherPass789!"})
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_expired_token_returns_400():
    """Un token expiré (> 30 min) doit être rejeté."""
    from app.models.password_reset_token import PasswordResetToken
    from app.models.user import User
    from app.core.security import create_refresh_token, hash_token
    import app.core.database as db_mod
    from sqlalchemy import select

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "r5@test.com", "password": "StrongPass123!"})

        async with db_mod.AsyncSessionLocal() as session:
            user_result = await session.execute(select(User).where(User.email == "r5@test.com"))
            user = user_result.scalar_one()
            expired = datetime.now(timezone.utc) - timedelta(hours=2)
            raw_token = create_refresh_token()
            token_obj = PasswordResetToken(
                user_id=user.id,
                token=hash_token(raw_token),
                expires_at=expired,
            )
            session.add(token_obj)
            await session.commit()

        r = await c.post(f"{BASE}/auth/reset-password", json={"token": raw_token, "password": "NewPass456!"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_reset_password_weak_password_rejected():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "r6@test.com", "password": "StrongPass123!"})

        with patch("app.api.v1.endpoints.auth.send_password_reset") as mock_send:
            await c.post(f"{BASE}/auth/forgot-password", json={"email": "r6@test.com"})

        raw_token = _extract_token_from_mock(mock_send)

        r = await c.post(f"{BASE}/auth/reset-password", json={"token": raw_token, "password": "abc"})
    # Pydantic validates min length at schema level
    assert r.status_code in (400, 422)
