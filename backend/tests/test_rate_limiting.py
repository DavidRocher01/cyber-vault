"""
Integration tests — rate limiting
Covers: newsletter/subscribe 5/minute, url-scans 10/minute.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, AsyncMock
from fastapi import HTTPException

from app.main import app

BASE = "/api/v1"


async def _auth_headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _raise_rate_limit(*args, **kwargs):
    """Side-effect that simulates the rate limit being exceeded."""
    raise HTTPException(status_code=429, detail="Trop de requêtes.")


# ── Newsletter subscribe ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_newsletter_subscribe_normal_returns_201():
    """A single subscribe call succeeds (rate limit not yet hit)."""
    with patch("app.api.v1.endpoints.newsletter.send_confirmation_email"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/newsletter/subscribe",
                json={"email": "ratelimit_test_ok@example.com"},
            )
    assert r.status_code == 201


@pytest.mark.asyncio
async def test_newsletter_subscribe_rate_limited_returns_429():
    """When the rate limit is exceeded the endpoint returns 429."""
    with patch("app.api.v1.endpoints.newsletter.send_confirmation_email"):
        with patch(
            "app.api.v1.endpoints.newsletter.limiter._check_request_limit",
            side_effect=_raise_rate_limit,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/newsletter/subscribe",
                    json={"email": "ratelimit_blocked@example.com"},
                )
    assert r.status_code == 429


# ── URL scans ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_url_scan_normal_returns_202():
    """A single url-scan call succeeds (rate limit not yet hit)."""
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _auth_headers(c, "urlrate@test.com")
            r = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
    assert r.status_code == 202


@pytest.mark.asyncio
async def test_url_scan_rate_limited_returns_429():
    """When the rate limit is exceeded url-scans returns 429."""
    with patch("app.api.v1.endpoints.url_scans.run_url_scan", new_callable=AsyncMock):
        with patch(
            "app.api.v1.endpoints.url_scans.limiter._check_request_limit",
            side_effect=_raise_rate_limit,
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                h = await _auth_headers(c, "urlrate2@test.com")
                r = await c.post(f"{BASE}/url-scans", json={"url": "https://example.com"}, headers=h)
    assert r.status_code == 429
