"""
Integration tests — /api/v1/quotes/{token}/accept|reject
Covers: 404 for unknown token, accept flow, reject flow, idempotency (already),
        409 conflicts (accept a rejected quote and vice versa).
"""
import pytest
from datetime import date
from httpx import ASGITransport, AsyncClient

import app.core.database as db_mod
from app.main import app
from app.models.quote import Quote

BASE = "/api/v1"


async def _seed_quote(token: str, status: str = "sent") -> None:
    async with db_mod.AsyncSessionLocal() as session:
        q = Quote(
            quote_number=f"DEV-2026-{token[:4]}",
            quote_seq=1,
            quote_year=2026,
            client_name="Test Client",
            client_email="client@test.com",
            subject="Audit Flash",
            items=[{"description": "Audit", "quantity": 1, "unit_price_cents": 9900}],
            total_cents=9900,
            status=status,
            issue_date=date.today(),
            acceptance_token=token,
        )
        session.add(q)
        await session.commit()


# ── 404 ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_unknown_token_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/no-such-token/accept")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_reject_unknown_token_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/no-such-token/reject")
    assert r.status_code == 404


# ── Happy path — accept ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_sent_quote_returns_accepted():
    await _seed_quote("tok-accept-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-accept-1/accept")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "accepted"
    assert data["already"] is False


@pytest.mark.asyncio
async def test_accept_sets_accepted_at_in_db():
    await _seed_quote("tok-accept-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/quotes/tok-accept-2/accept")

    from sqlalchemy import select
    async with db_mod.AsyncSessionLocal() as session:
        q = (await session.execute(
            select(Quote).where(Quote.acceptance_token == "tok-accept-2")
        )).scalar_one()
    assert q.status == "accepted"
    assert q.accepted_at is not None


# ── Happy path — reject ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reject_sent_quote_returns_rejected():
    await _seed_quote("tok-reject-1")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-reject-1/reject")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "rejected"
    assert data["already"] is False


@pytest.mark.asyncio
async def test_reject_sets_rejected_at_in_db():
    await _seed_quote("tok-reject-2")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(f"{BASE}/quotes/tok-reject-2/reject")

    from sqlalchemy import select
    async with db_mod.AsyncSessionLocal() as session:
        q = (await session.execute(
            select(Quote).where(Quote.acceptance_token == "tok-reject-2")
        )).scalar_one()
    assert q.status == "rejected"
    assert q.rejected_at is not None


# ── Idempotency ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_already_accepted_returns_already_true():
    await _seed_quote("tok-idem-1", status="accepted")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-idem-1/accept")
    assert r.status_code == 200
    assert r.json()["already"] is True


@pytest.mark.asyncio
async def test_reject_already_rejected_returns_already_true():
    await _seed_quote("tok-idem-2", status="rejected")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-idem-2/reject")
    assert r.status_code == 200
    assert r.json()["already"] is True


# ── 409 conflicts ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_accept_rejected_quote_returns_409():
    await _seed_quote("tok-conflict-1", status="rejected")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-conflict-1/accept")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_reject_accepted_quote_returns_409():
    await _seed_quote("tok-conflict-2", status="accepted")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-conflict-2/reject")
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_accept_expired_quote_returns_409():
    await _seed_quote("tok-expired-1", status="expired")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/quotes/tok-expired-1/accept")
    assert r.status_code == 409
