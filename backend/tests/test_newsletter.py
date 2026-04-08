"""
Integration tests — /api/v1/newsletter
Covers: double opt-in flow, confirm, unsubscribe redirects,
        admin stats/list/send-issue, auth guard, edge cases.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch, MagicMock, DEFAULT

from app.main import app
from app.models.newsletter_subscriber import NewsletterSubscriber
from sqlalchemy import select

BASE = "/api/v1"

# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_subscriber(email: str) -> NewsletterSubscriber | None:
    # Import at call time so conftest's fixture patch is applied
    import app.core.database as _db
    async with _db.AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
        )
        return result.scalar_one_or_none()


def _no_email():
    """Patch all newsletter email senders. Returns dict with mock keys via DEFAULT."""
    return patch.multiple(
        "app.api.v1.endpoints.newsletter",
        send_confirmation_email=DEFAULT,
        send_newsletter_welcome=DEFAULT,
        send_unsubscribe_confirmation=DEFAULT,
    )


def _admin_settings():
    """Patch settings so ADMIN_API_KEY is set."""
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    mock.FRONTEND_URL = "http://localhost:4200"
    return patch("app.api.v1.endpoints.newsletter.settings", mock)


# ── Subscribe ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_subscribe_new_returns_201_sends_confirmation():
    with _no_email() as mocks:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "newuser@test.com"})
    assert r.status_code == 201
    assert "boîte mail" in r.json()["message"]
    mocks["send_confirmation_email"].assert_called_once()
    mocks["send_newsletter_welcome"].assert_not_called()


@pytest.mark.asyncio
async def test_subscribe_creates_inactive_subscriber():
    with _no_email():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "inactive@test.com"})
    sub = await _get_subscriber("inactive@test.com")
    assert sub is not None
    assert sub.is_active is False
    assert sub.confirmation_token is not None
    assert sub.confirmed_at is None


@pytest.mark.asyncio
async def test_subscribe_invalid_email_returns_422():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_subscribe_duplicate_active_returns_409():
    """Already confirmed+active subscriber → 409."""
    with _no_email():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "dup409@test.com"})

    # Manually activate subscriber (simulate confirmed)
    async with __import__('app.core.database', fromlist=['AsyncSessionLocal']).AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == "dup409@test.com")
        )
        sub = result.scalar_one()
        sub.is_active = True
        await db.commit()

    with _no_email():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "dup409@test.com"})
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_subscribe_pending_resends_confirmation():
    """Unconfirmed subscriber re-subscribes → resend confirmation, not 409."""
    with _no_email() as mocks:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "pending@test.com"})
            mocks["send_confirmation_email"].reset_mock()
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "pending@test.com"})
    assert r.status_code == 201
    assert "renvoyé" in r.json()["message"]
    mocks["send_confirmation_email"].assert_called_once()


# ── Confirm ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_valid_token_activates_subscriber():
    with _no_email():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "confirm@test.com"})

    sub = await _get_subscriber("confirm@test.com")
    token = sub.confirmation_token

    with _no_email() as mocks:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as c:
            r = await c.get(f"{BASE}/newsletter/confirm?token={token}")

    assert r.status_code == 302
    assert "status=ok" in r.headers["location"]
    mocks["send_newsletter_welcome"].assert_called_once()

    sub = await _get_subscriber("confirm@test.com")
    assert sub.is_active is True
    assert sub.confirmed_at is not None
    assert sub.confirmation_token is None


@pytest.mark.asyncio
async def test_confirm_invalid_token_redirects_invalid():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as c:
        r = await c.get(f"{BASE}/newsletter/confirm?token=totally-fake-token")
    assert r.status_code == 302
    assert "status=invalid" in r.headers["location"]


# ── Unsubscribe ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unsubscribe_valid_token_deactivates_and_redirects():
    with _no_email():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "unsub@test.com"})

    # Activate subscriber
    async with __import__('app.core.database', fromlist=['AsyncSessionLocal']).AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == "unsub@test.com")
        )
        sub = result.scalar_one()
        sub.is_active = True
        token = sub.unsubscribe_token
        await db.commit()

    with _no_email() as mocks:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
        ) as c:
            r = await c.get(f"{BASE}/newsletter/unsubscribe?token={token}")

    assert r.status_code == 302
    assert "status=ok" in r.headers["location"]
    mocks["send_unsubscribe_confirmation"].assert_called_once()

    sub = await _get_subscriber("unsub@test.com")
    assert sub.is_active is False


@pytest.mark.asyncio
async def test_unsubscribe_invalid_token_redirects_invalid():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=False
    ) as c:
        r = await c.get(f"{BASE}/newsletter/unsubscribe?token=fake-token-xyz")
    assert r.status_code == 302
    assert "status=invalid" in r.headers["location"]


@pytest.mark.asyncio
async def test_resubscribe_confirmed_unsubscribed():
    """Previously confirmed+unsubscribed: re-subscribe reactivates directly (no confirm email)."""
    with _no_email():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "resub@test.com"})

    # Simulate confirmed + then unsubscribed
    async with __import__('app.core.database', fromlist=['AsyncSessionLocal']).AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == "resub@test.com")
        )
        sub = result.scalar_one()
        from datetime import datetime, timezone
        sub.is_active = False
        sub.confirmed_at = datetime.now(timezone.utc)
        sub.confirmation_token = None
        await db.commit()

    with _no_email() as mocks:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "resub@test.com"})

    assert r.status_code == 201
    assert "Réabonnement" in r.json()["message"]
    mocks["send_newsletter_welcome"].assert_called_once()
    mocks["send_confirmation_email"].assert_not_called()


# ── Admin — auth guard ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/stats")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_wrong_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/stats", headers={"x-admin-key": "wrong"})
    assert r.status_code == 403


# ── Admin — stats ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_stats_valid_key_returns_counts():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/stats", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    data = r.json()
    assert "total" in data
    assert "active" in data
    assert "pending_confirmation" in data
    assert data["total"] >= 0


# ── Admin — subscribers list ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_subscribers_returns_list():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/subscribers", headers={"x-admin-key": "test-secret-key"})
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ── Admin — send issue ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_send_issue_returns_sent_count():
    issue_payload = {
        "edition": 1,
        "flash_title": "Test Attack",
        "flash_body": "A major attack happened.",
        "reflex_title": "Enable MFA",
        "reflex_body": "Enable MFA on all accounts.",
        "legal_title": "NIS2 Update",
        "legal_body": "New NIS2 requirements apply.",
    }
    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.send_newsletter_issue") as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/newsletter/admin/send-issue",
                    json=issue_payload,
                    headers={"x-admin-key": "test-secret-key"},
                )
    assert r.status_code == 200
    data = r.json()
    assert "sent" in data
    assert "message" in data
    assert data["sent"] >= 0


@pytest.mark.asyncio
async def test_admin_send_issue_no_key_returns_403():
    issue_payload = {
        "edition": 1,
        "flash_title": "T", "flash_body": "T",
        "reflex_title": "T", "reflex_body": "T",
        "legal_title": "T", "legal_body": "T",
    }
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/admin/send-issue", json=issue_payload)
    assert r.status_code == 403
