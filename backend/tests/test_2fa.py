"""
Tests d'intégration — Double authentification (2FA / TOTP)

Scénarios couverts :
  - Setup   : génère secret + QR code, stocke le secret (non activé)
  - Enable  : code valide → totp_enabled = True
  - Enable  : code invalide → 400
  - Enable  : sans setup préalable → 400
  - Login   : utilisateur 2FA sans code → requires_2fa: True
  - Login   : utilisateur 2FA avec code valide → tokens
  - Login   : utilisateur 2FA avec code invalide → 401
  - Login   : utilisateur sans 2FA → tokens normalement
  - Disable : mot de passe + code valide → totp_enabled = False, secret effacé
  - Disable : mot de passe incorrect → 401
  - Disable : code TOTP invalide → 400
  - Disable : 2FA non activée → 400
  - /users/me expose totp_enabled correctement
"""

import pyotp
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"
PWD = "StrongPass123!"


# ── Helpers ──────────────────────────────────────────────────────────────────

async def _register_login(client: AsyncClient, email: str) -> dict:
    """Register user and return auth headers."""
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": PWD})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PWD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _setup_and_enable_2fa(client: AsyncClient, headers: dict) -> str:
    """Run setup + enable flow, return the TOTP secret."""
    setup = await client.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    enable = await client.post(
        f"{BASE}/users/me/2fa/enable",
        headers=headers,
        json={"code": code},
    )
    assert enable.status_code == 200
    assert enable.json()["totp_enabled"] is True
    return secret


# ── Setup endpoint ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_setup_2fa_returns_qr_and_secret():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "setup@2fa.com")
        r = await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})

    assert r.status_code == 200
    data = r.json()
    assert "qr_code_b64" in data
    assert "secret" in data
    assert len(data["secret"]) >= 16  # base32 TOTP secret
    assert len(data["qr_code_b64"]) > 100  # base64 PNG


@pytest.mark.asyncio
async def test_setup_2fa_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/users/me/2fa/setup", json={})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_setup_2fa_does_not_enable_totp_yet():
    """Setup stores the secret but totp_enabled must stay False until verified."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "notyet@2fa.com")
        await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})
        me = await c.get(f"{BASE}/users/me", headers=headers)

    assert me.json()["totp_enabled"] is False


# ── Enable endpoint ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_enable_2fa_with_valid_code():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "enable@2fa.com")
        setup = await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})
        secret = setup.json()["secret"]
        code = pyotp.TOTP(secret).now()

        r = await c.post(f"{BASE}/users/me/2fa/enable", headers=headers, json={"code": code})

    assert r.status_code == 200
    assert r.json()["totp_enabled"] is True


@pytest.mark.asyncio
async def test_enable_2fa_with_invalid_code_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "badenab@2fa.com")
        await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})

        r = await c.post(f"{BASE}/users/me/2fa/enable", headers=headers, json={"code": "000000"})

    assert r.status_code == 400


@pytest.mark.asyncio
async def test_enable_2fa_without_setup_returns_400():
    """Cannot enable without calling setup first."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "nosetup@2fa.com")
        r = await c.post(f"{BASE}/users/me/2fa/enable", headers=headers, json={"code": "123456"})

    assert r.status_code == 400


# ── Login flow with 2FA ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_with_2fa_enabled_no_code_returns_requires_2fa():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "login2fa@2fa.com")
        await _setup_and_enable_2fa(c, headers)

        r = await c.post(f"{BASE}/auth/login", json={"email": "login2fa@2fa.com", "password": PWD})

    assert r.status_code == 200
    assert r.json() == {"requires_2fa": True}


@pytest.mark.asyncio
async def test_login_with_2fa_valid_code_returns_tokens():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "toklogin@2fa.com")
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()

        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "toklogin@2fa.com", "password": PWD, "totp_code": code},
        )

    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_with_2fa_invalid_code_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "badcode@2fa.com")
        await _setup_and_enable_2fa(c, headers)

        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "badcode@2fa.com", "password": PWD, "totp_code": "000000"},
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_login_without_2fa_returns_tokens_normally():
    """User without 2FA must not be affected by the new flow."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "no2fa@test.com", "password": PWD})
        r = await c.post(f"{BASE}/auth/login", json={"email": "no2fa@test.com", "password": PWD})

    assert r.status_code == 200
    assert "access_token" in r.json()


# ── Disable endpoint ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_disable_2fa_with_valid_credentials():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "disable@2fa.com")
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()

        r = await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": PWD, "code": code},
        )

    assert r.status_code == 200
    assert r.json()["totp_enabled"] is False


@pytest.mark.asyncio
async def test_disable_2fa_clears_secret():
    """After disable, a login attempt must not hit the 2FA gate."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "clearsecret@2fa.com")
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()
        await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": PWD, "code": code},
        )

        # Normal login must return tokens, not requires_2fa
        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": "clearsecret@2fa.com", "password": PWD},
        )

    assert "access_token" in r.json()


@pytest.mark.asyncio
async def test_disable_2fa_wrong_password_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "wrongpw@2fa.com")
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()

        r = await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": "WrongPassword!", "code": code},
        )

    assert r.status_code == 401


@pytest.mark.asyncio
async def test_disable_2fa_wrong_totp_code_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "wrongotp@2fa.com")
        await _setup_and_enable_2fa(c, headers)

        r = await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": PWD, "code": "000000"},
        )

    assert r.status_code == 400


@pytest.mark.asyncio
async def test_disable_2fa_not_enabled_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "nodisable@2fa.com")

        r = await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": PWD, "code": "123456"},
        )

    assert r.status_code == 400


# ── /users/me reflects totp_enabled ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_users_me_totp_enabled_field_false_by_default():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "mefield@2fa.com")
        r = await c.get(f"{BASE}/users/me", headers=headers)

    assert r.json()["totp_enabled"] is False


@pytest.mark.asyncio
async def test_users_me_totp_enabled_field_true_after_enable():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, "mefieldtrue@2fa.com")
        await _setup_and_enable_2fa(c, headers)
        r = await c.get(f"{BASE}/users/me", headers=headers)

    assert r.json()["totp_enabled"] is True
