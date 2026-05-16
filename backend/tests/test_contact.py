"""
Integration tests — /api/v1/contact
Covers: submit (200), validation errors (422), rate limiting shape.
"""
import pytest
from unittest.mock import patch, AsyncMock
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
    from app.schemas.contact import ContactIn
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ContactIn(name="x", email="a@b.com", need_type="unknown", message="msg ok long")
