"""
Integration tests — /api/v1/contact
Covers: submit (200), validation errors (422), admin list/update endpoints.
"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"

VALID_PAYLOAD = {
    "name": "Jean Dupont",
    "email": "jean@example.com",
    "phone": "06 12 34 56 78",
    "need_type": "audit-flash",
    "site_url": "https://monsite.fr",
    "message": "Je souhaite un audit de mon site vitrine.",
}


@pytest.mark.asyncio
async def test_contact_submit_returns_200():
    with patch("app.api.v1.endpoints.contact.send_contact_email") as mock_send:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/contact", json=VALID_PAYLOAD)
    assert r.status_code == 200
    assert "envoyé" in r.json()["message"]


@pytest.mark.asyncio
async def test_contact_missing_name_returns_422():
    payload = {**VALID_PAYLOAD, "name": ""}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/contact", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_contact_invalid_email_returns_422():
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/contact", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_contact_invalid_need_type_returns_422():
    payload = {**VALID_PAYLOAD, "need_type": "invalid-type"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/contact", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_contact_message_too_short_returns_422():
    payload = {**VALID_PAYLOAD, "message": "court"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/contact", json=payload)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_contact_without_optional_fields():
    payload = {
        "name": "Marie Martin",
        "email": "marie@example.com",
        "need_type": "pentest",
        "message": "Je veux un pentest léger pour mon application.",
    }
    with patch("app.api.v1.endpoints.contact.send_contact_email"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/contact", json=payload)
    assert r.status_code == 200


def test_contact_need_type_schema_validation():
    """All valid need_type values pass Pydantic validation without HTTP overhead."""
    from app.schemas.contact import ContactIn

    for nt in ["audit-flash", "audit-app", "pentest", "abonnement", "autre"]:
        obj = ContactIn(
            name="Test User",
            email="test@example.com",
            need_type=nt,
            message="Message de test valide.",
        )
        assert obj.need_type == nt


def test_contact_invalid_need_type_schema():
    """Unknown need_type is rejected by schema."""
    from pydantic import ValidationError

    from app.schemas.contact import ContactIn

    with pytest.raises(ValidationError):
        ContactIn(name="x", email="a@b.com", need_type="unknown", message="msg ok long")


# ── Admin helpers ──────────────────────────────────────────────────────────────


@contextmanager
def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    mock.CONTACT_EMAIL = "admin@test.com"
    with (
        patch("app.api.v1.endpoints.contact.settings", mock),
        patch("app.core.deps.settings", mock),
    ):
        yield


async def _submit_contact(client, name="Jean Dupont"):
    with patch("app.api.v1.endpoints.contact.send_contact_email"):
        return await client.post(
            f"{BASE}/contact",
            json={
                "name": name,
                "email": "jean@example.com",
                "need_type": "audit-flash",
                "message": "Je souhaite un audit de mon site vitrine.",
            },
        )


# ── Admin — auth guard ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_messages_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/contact/admin/messages")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_messages_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/contact/admin/messages", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── Admin — list messages ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_messages_valid_key_returns_list():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                f"{BASE}/contact/admin/messages",
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_messages_shows_submitted_message():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await _submit_contact(c)
            r = await c.get(
                f"{BASE}/contact/admin/messages",
                headers={"x-admin-key": "test-secret-key"},
            )
    messages = r.json()
    assert len(messages) == 1
    assert messages[0]["name"] == "Jean Dupont"
    assert messages[0]["status"] == "new"


@pytest.mark.asyncio
async def test_admin_messages_response_has_required_fields():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await _submit_contact(c)
            r = await c.get(
                f"{BASE}/contact/admin/messages",
                headers={"x-admin-key": "test-secret-key"},
            )
    msg = r.json()[0]
    for key in (
        "id",
        "name",
        "email",
        "phone",
        "need_type",
        "site_url",
        "message",
        "status",
        "created_at",
    ):
        assert key in msg, f"Missing key: {key}"


# ── Admin — update status ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_update_status_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(f"{BASE}/contact/admin/messages/1/status", json={"status": "handled"})
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_status_to_handled():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await _submit_contact(c)
            msgs = await c.get(
                f"{BASE}/contact/admin/messages",
                headers={"x-admin-key": "test-secret-key"},
            )
            msg_id = msgs.json()[0]["id"]
            r = await c.patch(
                f"{BASE}/contact/admin/messages/{msg_id}/status",
                json={"status": "handled"},
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    assert "mis à jour" in r.json()["message"]


@pytest.mark.asyncio
async def test_admin_update_status_to_archived():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await _submit_contact(c)
            msgs = await c.get(
                f"{BASE}/contact/admin/messages",
                headers={"x-admin-key": "test-secret-key"},
            )
            msg_id = msgs.json()[0]["id"]
            r = await c.patch(
                f"{BASE}/contact/admin/messages/{msg_id}/status",
                json={"status": "archived"},
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_admin_update_status_invalid_value_returns_422():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await _submit_contact(c)
            msgs = await c.get(
                f"{BASE}/contact/admin/messages",
                headers={"x-admin-key": "test-secret-key"},
            )
            msg_id = msgs.json()[0]["id"]
            r = await c.patch(
                f"{BASE}/contact/admin/messages/{msg_id}/status",
                json={"status": "invalid"},
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_update_status_unknown_id_returns_404():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.patch(
                f"{BASE}/contact/admin/messages/99999/status",
                json={"status": "handled"},
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 404
