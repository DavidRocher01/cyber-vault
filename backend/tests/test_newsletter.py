"""
Integration tests — /api/v1/newsletter
Covers: subscribe (201), duplicate 409, re-subscribe after unsubscribe,
        unsubscribe (200), invalid token (404), email validation.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock

from app.main import app

BASE = "/api/v1"


@pytest.mark.asyncio
async def test_subscribe_returns_201():
    with patch("app.api.v1.endpoints.newsletter.send_newsletter_welcome", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "sub1@test.com"})
    assert r.status_code == 201
    assert "message" in r.json()


@pytest.mark.asyncio
async def test_subscribe_invalid_email_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_subscribe_duplicate_returns_409():
    with patch("app.api.v1.endpoints.newsletter.send_newsletter_welcome", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "dup@test.com"})
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "dup@test.com"})
    assert r.status_code == 409
    assert "abonné" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_unsubscribe_valid_token_returns_200():
    with patch("app.api.v1.endpoints.newsletter.send_newsletter_welcome", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Subscribe first to get token
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "unsub@test.com"})

            # Fetch token via DB
            from app.core.database import AsyncSessionLocal
            from app.models.newsletter_subscriber import NewsletterSubscriber
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(NewsletterSubscriber).where(NewsletterSubscriber.email == "unsub@test.com")
                )
                sub = result.scalar_one()
                token = sub.unsubscribe_token

            r = await c.get(f"{BASE}/newsletter/unsubscribe?token={token}")
    assert r.status_code == 200
    assert "Désabonnement" in r.json()["message"]


@pytest.mark.asyncio
async def test_unsubscribe_invalid_token_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/newsletter/unsubscribe?token=fake-invalid-token")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_resubscribe_after_unsubscribe():
    """After unsubscribing, the same email can subscribe again (re-subscribe flow)."""
    with patch("app.api.v1.endpoints.newsletter.send_newsletter_welcome", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            # Initial subscribe
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "resub@test.com"})

            # Fetch token and unsubscribe
            from app.core.database import AsyncSessionLocal
            from app.models.newsletter_subscriber import NewsletterSubscriber
            from sqlalchemy import select
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(NewsletterSubscriber).where(NewsletterSubscriber.email == "resub@test.com")
                )
                token = result.scalar_one().unsubscribe_token
            await c.get(f"{BASE}/newsletter/unsubscribe?token={token}")

            # Re-subscribe — must succeed (not 409)
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "resub@test.com"})
    assert r.status_code == 201
    assert "Réabonnement" in r.json()["message"]


@pytest.mark.asyncio
async def test_subscribe_confirmation_message_present():
    with patch("app.api.v1.endpoints.newsletter.send_newsletter_welcome", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "msg@test.com"})
    assert "Inscription confirmée" in r.json()["message"]
