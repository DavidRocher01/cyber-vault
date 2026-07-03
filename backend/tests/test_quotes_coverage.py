"""
Integration tests — quote endpoints, non-happy-path / limit branches.

Targets branches NOT covered by test_quote_acceptance.py and test_admin_quotes.py:
  * public reject flow: reject on an *expired* quote → 409 (only reject-of-accepted
    was tested before)
  * public accept: idempotent accept on an already-accepted quote returns the
    stored quote_number
  * public flows against a quote whose acceptance_token is used by another client
    (token is the sole authorization key → only the exact token works)
  * admin create with user_email matching an existing user → user_id is linked
  * admin create with user_email that matches no user → user_id stays None
  * admin create with an explicit issue_date
  * admin create with client_address=None serialized safely
  * admin list ordering (created_at desc) with several quotes
"""

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.core.database as db_mod
from app.main import app
from app.models.quote import Quote
from app.models.user import User

BASE = "/api/v1"


@contextmanager
def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-admin-key"
    with patch("app.api.v1.endpoints.admin_quotes.settings", mock):
        yield


_HEADERS = {"x-admin-key": "test-admin-key"}

_QUOTE_PAYLOAD = {
    "client_name": "Acme Corp",
    "client_email": "acme@example.com",
    "client_address": "12 rue de la Paix, Paris",
    "subject": "Audit de sécurité",
    "items": [{"description": "Audit externe", "quantity": 2, "unit_price_cents": 60000}],
    "validity_days": 30,
}


async def _seed_quote(token: str, status: str = "sent", seq: int = 1) -> None:
    async with db_mod.AsyncSessionLocal() as session:
        q = Quote(
            quote_number=f"DEV-2026-{token[:4]}-{seq}",
            quote_seq=seq,
            quote_year=2026,
            client_name="Seed Client",
            client_email="seed@test.com",
            subject="Audit Flash",
            items=[{"description": "Audit", "quantity": 1, "unit_price_cents": 9900}],
            total_cents=9900,
            status=status,
            issue_date=date.today(),
            acceptance_token=token,
        )
        session.add(q)
        await session.commit()


# ── Public: reject an expired quote → 409 (uncovered branch) ────────────────────


async def test_reject_expired_quote_returns_409():
    await _seed_quote("tok-rej-expired", status="expired")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-rej-expired/reject")
    assert r.status_code == 409
    assert "expired" in r.json()["detail"]


# ── Public: idempotent accept echoes the stored quote_number ────────────────────


async def test_accept_already_accepted_echoes_quote_number():
    await _seed_quote("tok-idem-accept", status="accepted")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-idem-accept/accept")
    assert r.status_code == 200
    data = r.json()
    assert data["already"] is True
    assert data["status"] == "accepted"
    assert data["quote_number"] == "DEV-2026-tok--1"


# ── Public: token is the sole auth key — a different token 404s, DB untouched ────


async def test_accept_wrong_token_does_not_touch_other_quote():
    """A quote exists under one token; accepting a *different* token must 404
    and leave the real quote in its original 'sent' state (no cross-quote write)."""
    await _seed_quote("real-token-xyz", status="sent")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/some-other-token/accept")
    assert r.status_code == 404

    async with db_mod.AsyncSessionLocal() as session:
        q = (
            await session.execute(select(Quote).where(Quote.acceptance_token == "real-token-xyz"))
        ).scalar_one()
    assert q.status == "sent"
    assert q.accepted_at is None


async def test_reject_wrong_token_does_not_touch_other_quote():
    await _seed_quote("real-token-abc", status="sent")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/nope-token/reject")
    assert r.status_code == 404

    async with db_mod.AsyncSessionLocal() as session:
        q = (
            await session.execute(select(Quote).where(Quote.acceptance_token == "real-token-abc"))
        ).scalar_one()
    assert q.status == "sent"
    assert q.rejected_at is None


# ── Admin create: user_email links to an existing user (uncovered branch) ────────


async def test_admin_create_quote_links_existing_user():
    async with db_mod.AsyncSessionLocal() as session:
        user = User(email="linked@test.com", hashed_password="x")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/admin/quotes",
                    json={**_QUOTE_PAYLOAD, "user_email": "linked@test.com"},
                    headers=_HEADERS,
                )
    assert r.status_code == 201
    quote_id = r.json()["id"]

    async with db_mod.AsyncSessionLocal() as session:
        q = (await session.execute(select(Quote).where(Quote.id == quote_id))).scalar_one()
    assert q.user_id == user_id


# ── Admin create: user_email with no matching user → user_id stays None ──────────


async def test_admin_create_quote_unknown_user_email_leaves_user_id_none():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/admin/quotes",
                    json={**_QUOTE_PAYLOAD, "user_email": "ghost@nowhere.test"},
                    headers=_HEADERS,
                )
    assert r.status_code == 201
    quote_id = r.json()["id"]

    async with db_mod.AsyncSessionLocal() as session:
        q = (await session.execute(select(Quote).where(Quote.id == quote_id))).scalar_one()
    assert q.user_id is None


# ── Admin create: explicit issue_date is honoured ────────────────────────────────


async def test_admin_create_quote_with_explicit_issue_date():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/admin/quotes",
                    json={**_QUOTE_PAYLOAD, "issue_date": "2026-01-15"},
                    headers=_HEADERS,
                )
    assert r.status_code == 201
    data = r.json()
    assert data["issue_date"] == "2026-01-15"
    # quote_number embeds the year taken from issue_date
    assert data["quote_number"].startswith("DEVIS-2026-")
    # 2 × 60000 = 120000 cents → 1200.0 €
    assert data["total_cents"] == 120000
    assert data["total_eur"] == 1200.0


# ── Admin create: client_address None serializes cleanly ─────────────────────────


async def test_admin_create_quote_without_address_serializes_none():
    payload = {k: v for k, v in _QUOTE_PAYLOAD.items() if k != "client_address"}
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(f"{BASE}/admin/quotes", json=payload, headers=_HEADERS)
    assert r.status_code == 201
    assert r.json()["client_address"] is None


# ── Admin list: ordering is created_at desc (most recent first) ──────────────────


async def test_admin_list_quotes_orders_newest_first():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_quotes.send_quote_by_email"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                first = await c.post(
                    f"{BASE}/admin/quotes",
                    json={**_QUOTE_PAYLOAD, "subject": "First"},
                    headers=_HEADERS,
                )
                second = await c.post(
                    f"{BASE}/admin/quotes",
                    json={**_QUOTE_PAYLOAD, "subject": "Second"},
                    headers=_HEADERS,
                )
                r = await c.get(f"{BASE}/admin/quotes", headers=_HEADERS)

    assert first.status_code == 201
    assert second.status_code == 201
    body = r.json()
    assert len(body) >= 2
    subjects = [q["subject"] for q in body]
    # both present, and the two we created appear in desc order of creation
    assert "First" in subjects and "Second" in subjects
    assert subjects.index("Second") < subjects.index("First")
