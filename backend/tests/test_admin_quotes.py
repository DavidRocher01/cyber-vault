"""
Integration tests — /api/v1/admin/quotes
Covers: auth guard, create quote, list quotes, PDF download (404 + success).
"""
import pytest
from contextlib import contextmanager
from unittest.mock import patch, MagicMock
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


@contextmanager
def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-admin-key"
    with patch("app.api.v1.endpoints.admin_quotes.settings", mock):
        yield


_QUOTE_PAYLOAD = {
    "client_name": "Acme Corp",
    "client_email": "acme@example.com",
    "client_address": "12 rue de la Paix, Paris",
    "subject": "Audit de sécurité",
    "items": [
        {"description": "Audit externe", "quantity": 1, "unit_price_cents": 120000},
        {"description": "Rapport", "quantity": 1, "unit_price_cents": 30000},
    ],
    "validity_days": 30,
}


# ── Auth guard ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_quotes_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/quotes")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_quotes_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/quotes", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── List quotes ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_list_quotes_empty_returns_list():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/quotes", headers={"x-admin-key": "test-admin-key"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Create quote ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_create_quote_returns_201():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/admin/quotes",
                    json=_QUOTE_PAYLOAD,
                    headers={"x-admin-key": "test-admin-key"},
                )
    assert r.status_code == 201
    data = r.json()
    assert data["client_name"] == "Acme Corp"
    assert data["client_email"] == "acme@example.com"
    assert data["total_cents"] == 150000
    assert "quote_number" in data
    assert data["status"] in ("draft", "sent")


@pytest.mark.asyncio
async def test_admin_create_quote_appears_in_list():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                await c.post(
                    f"{BASE}/admin/quotes",
                    json=_QUOTE_PAYLOAD,
                    headers={"x-admin-key": "test-admin-key"},
                )
                r = await c.get(f"{BASE}/admin/quotes", headers={"x-admin-key": "test-admin-key"})
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert any(q["client_name"] == "Acme Corp" for q in r.json())


@pytest.mark.asyncio
async def test_admin_create_quote_invalid_items_returns_422():
    """Empty items list → 422 from field validator."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/admin/quotes",
                json={**_QUOTE_PAYLOAD, "items": []},
                headers={"x-admin-key": "test-admin-key"},
            )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_create_quote_negative_quantity_returns_422():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/admin/quotes",
                json={
                    **_QUOTE_PAYLOAD,
                    "items": [{"description": "Bad", "quantity": 0, "unit_price_cents": 1000}],
                },
                headers={"x-admin-key": "test-admin-key"},
            )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_create_quote_negative_price_returns_422():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/admin/quotes",
                json={
                    **_QUOTE_PAYLOAD,
                    "items": [{"description": "Bad", "quantity": 1, "unit_price_cents": -1}],
                },
                headers={"x-admin-key": "test-admin-key"},
            )
    assert r.status_code == 422


# ── PDF download ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_download_quote_pdf_not_found_returns_404():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/admin/quotes/99999/pdf", headers={"x-admin-key": "test-admin-key"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_download_quote_pdf_returns_pdf():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            with patch("app.api.v1.endpoints.admin_quotes.generate_quote_pdf", return_value=b"%PDF-1.4 fake"):
                async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                    created = await c.post(
                        f"{BASE}/admin/quotes",
                        json=_QUOTE_PAYLOAD,
                        headers={"x-admin-key": "test-admin-key"},
                    )
                    quote_id = created.json()["id"]
                    r = await c.get(
                        f"{BASE}/admin/quotes/{quote_id}/pdf",
                        headers={"x-admin-key": "test-admin-key"},
                    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
