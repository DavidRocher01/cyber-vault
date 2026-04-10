"""
Integration tests — user profile endpoints.
Covers: update email, update password, export RGPD, delete account.
Parcours #43–#49.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


async def _auth(client: AsyncClient, email: str, password: str = "StrongPass123!") -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": password})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ── Update email ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_email_success():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email1@test.com")
        r = await c.put(f"{BASE}/users/me/email", headers=h, json={
            "email": "newemail1@test.com",
            "current_password": "StrongPass123!",
        })
    assert r.status_code == 200
    assert r.json()["email"] == "newemail1@test.com"


@pytest.mark.asyncio
async def test_update_email_wrong_password_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email2@test.com")
        r = await c.put(f"{BASE}/users/me/email", headers=h, json={
            "email": "newemail2@test.com",
            "current_password": "WrongPassword!",
        })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_email_duplicate_returns_409():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/auth/register", json={"email": "taken@test.com", "password": "StrongPass123!"})
        h = await _auth(c, "email3@test.com")
        r = await c.put(f"{BASE}/users/me/email", headers=h, json={
            "email": "taken@test.com",
            "current_password": "StrongPass123!",
        })
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_update_email_invalid_format_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "email4@test.com")
        r = await c.put(f"{BASE}/users/me/email", headers=h, json={
            "email": "not-an-email",
            "current_password": "StrongPass123!",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_email_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(f"{BASE}/users/me/email", json={
            "email": "x@test.com",
            "current_password": "any",
        })
    assert r.status_code == 403


# ── Update password ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_password_success_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw1@test.com")
        r = await c.put(f"{BASE}/users/me/password", headers=h, json={
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
        })
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_update_password_allows_login_with_new_password():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw2@test.com")
        await c.put(f"{BASE}/users/me/password", headers=h, json={
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
        })
        login = await c.post(f"{BASE}/auth/login", json={"email": "pw2@test.com", "password": "NewStrongPass456!"})
    assert login.status_code == 200


@pytest.mark.asyncio
async def test_update_password_old_password_no_longer_works():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw3@test.com")
        await c.put(f"{BASE}/users/me/password", headers=h, json={
            "current_password": "StrongPass123!",
            "new_password": "NewStrongPass456!",
        })
        old = await c.post(f"{BASE}/auth/login", json={"email": "pw3@test.com", "password": "StrongPass123!"})
    assert old.status_code == 401


@pytest.mark.asyncio
async def test_update_password_wrong_current_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw4@test.com")
        r = await c.put(f"{BASE}/users/me/password", headers=h, json={
            "current_password": "WrongPassword!",
            "new_password": "NewStrongPass456!",
        })
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_update_password_too_short_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "pw5@test.com")
        r = await c.put(f"{BASE}/users/me/password", headers=h, json={
            "current_password": "StrongPass123!",
            "new_password": "short",
        })
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_update_password_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.put(f"{BASE}/users/me/password", json={
            "current_password": "any",
            "new_password": "NewStrongPass456!",
        })
    assert r.status_code == 403


# ── Export RGPD ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_export_my_data_returns_json():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export1@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")


@pytest.mark.asyncio
async def test_export_my_data_contains_account_info():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export2@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    data = r.json()
    assert "account" in data
    assert data["account"]["email"] == "export2@test.com"


@pytest.mark.asyncio
async def test_export_my_data_contains_sites_and_scans_keys():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export3@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    data = r.json()
    assert "sites" in data
    assert "scans" in data
    assert isinstance(data["sites"], list)
    assert isinstance(data["scans"], list)


@pytest.mark.asyncio
async def test_export_my_data_contains_exported_at():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export4@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    assert "exported_at" in r.json()


@pytest.mark.asyncio
async def test_export_my_data_has_content_disposition_header():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "export5@test.com")
        r = await c.get(f"{BASE}/users/me/export", headers=h)
    assert "content-disposition" in r.headers
    assert "attachment" in r.headers["content-disposition"]


@pytest.mark.asyncio
async def test_export_my_data_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/users/me/export")
    assert r.status_code == 403


# ── Delete account ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_account_success_returns_204():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del1@test.com")
        r = await c.request("DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"})
    assert r.status_code == 204


@pytest.mark.asyncio
async def test_delete_account_prevents_further_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del2@test.com")
        await c.request("DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"})
        login = await c.post(f"{BASE}/auth/login", json={"email": "del2@test.com", "password": "StrongPass123!"})
    assert login.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_wrong_password_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del3@test.com")
        r = await c.request("DELETE", f"{BASE}/users/me", headers=h, json={"password": "WrongPassword!"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_unauthenticated_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.request("DELETE", f"{BASE}/users/me", json={"password": "any"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_delete_account_token_no_longer_valid_after_deletion():
    """Après suppression, l'access token existant ne doit plus fonctionner."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _auth(c, "del4@test.com")
        await c.request("DELETE", f"{BASE}/users/me", headers=h, json={"password": "StrongPass123!"})
        r = await c.get(f"{BASE}/users/me", headers=h)
    assert r.status_code == 401
