"""
Integration tests — /api/v1/admin/quotes
Covers: auth guard, create quote, list quotes, PDF download (404 + success).
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"


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
# Sans authentification, ce n'est plus une cle absente (403) mais une
# identite absente (401) : le back-office ne connait plus de porte anonyme.
async def test_admin_quotes_sans_authentification_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/quotes")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_admin_quotes_wrong_key_returns_403(entetes_non_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/quotes", headers=entetes_non_admin)
    assert r.status_code == 403


# ── List quotes ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_list_quotes_empty_returns_list(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/quotes", headers=entetes_admin)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Create quote ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_create_quote_returns_201(entetes_admin):
    with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/admin/quotes",
                json=_QUOTE_PAYLOAD,
                headers=entetes_admin,
            )
    assert r.status_code == 201
    data = r.json()
    assert data["client_name"] == "Acme Corp"
    assert data["client_email"] == "acme@example.com"
    assert data["total_cents"] == 150000
    assert "quote_number" in data
    assert data["status"] in ("draft", "sent")


@pytest.mark.asyncio
async def test_admin_create_quote_appears_in_list(entetes_admin):
    with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(
                f"{BASE}/admin/quotes",
                json=_QUOTE_PAYLOAD,
                headers=entetes_admin,
            )
            r = await c.get(f"{BASE}/admin/quotes", headers=entetes_admin)
    assert r.status_code == 200
    assert len(r.json()) >= 1
    assert any(q["client_name"] == "Acme Corp" for q in r.json())


@pytest.mark.asyncio
async def test_admin_create_quote_invalid_items_returns_422(entetes_admin):
    """Empty items list → 422 from field validator."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/admin/quotes",
            json={**_QUOTE_PAYLOAD, "items": []},
            headers=entetes_admin,
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_create_quote_negative_quantity_returns_422(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/admin/quotes",
            json={
                **_QUOTE_PAYLOAD,
                "items": [{"description": "Bad", "quantity": 0, "unit_price_cents": 1000}],
            },
            headers=entetes_admin,
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_create_quote_negative_price_returns_422(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"{BASE}/admin/quotes",
            json={
                **_QUOTE_PAYLOAD,
                "items": [{"description": "Bad", "quantity": 1, "unit_price_cents": -1}],
            },
            headers=entetes_admin,
        )
    assert r.status_code == 422


# ── PDF download ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_download_quote_pdf_not_found_returns_404(entetes_admin):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"{BASE}/admin/quotes/99999/pdf",
            headers=entetes_admin,
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_admin_download_quote_pdf_returns_pdf(entetes_admin):
    with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
        with patch(
            "app.api.v1.endpoints.admin_quotes.generate_quote_pdf",
            return_value=b"%PDF-1.4 fake",
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                created = await c.post(
                    f"{BASE}/admin/quotes",
                    json=_QUOTE_PAYLOAD,
                    headers=entetes_admin,
                )
                quote_id = created.json()["id"]
                r = await c.get(
                    f"{BASE}/admin/quotes/{quote_id}/pdf",
                    headers=entetes_admin,
                )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
