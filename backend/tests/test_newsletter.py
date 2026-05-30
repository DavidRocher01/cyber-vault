"""
Integration tests — /api/v1/newsletter
Covers: double opt-in flow, confirm, unsubscribe redirects,
        admin stats/list/send-issue, auth guard, edge cases.
"""

from contextlib import contextmanager
from datetime import UTC
from unittest.mock import DEFAULT, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.newsletter_subscriber import NewsletterSubscriber

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


@contextmanager
def _admin_settings():
    """Patch settings so ADMIN_API_KEY is set."""
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    mock.FRONTEND_URL = "http://localhost:4200"
    with (
        patch("app.api.v1.endpoints.newsletter.settings", mock),
        patch("app.core.deps.settings", mock),
    ):
        yield


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
    async with __import__(
        "app.core.database", fromlist=["AsyncSessionLocal"]
    ).AsyncSessionLocal() as db:
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
    with _no_email() as mocks_sub:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "confirm@test.com"})

    # Extract the raw token from the confirm URL passed to send_confirmation_email
    confirm_url = mocks_sub["send_confirmation_email"].call_args[0][1]
    token = confirm_url.split("token=")[1]

    with _no_email() as mocks:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
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
    async with __import__(
        "app.core.database", fromlist=["AsyncSessionLocal"]
    ).AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == "unsub@test.com")
        )
        sub = result.scalar_one()
        sub.is_active = True
        token = sub.unsubscribe_token
        await db.commit()

    with _no_email() as mocks:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            follow_redirects=False,
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
    async with __import__(
        "app.core.database", fromlist=["AsyncSessionLocal"]
    ).AsyncSessionLocal() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == "resub@test.com")
        )
        sub = result.scalar_one()
        from datetime import datetime

        sub.is_active = False
        sub.confirmed_at = datetime.now(UTC)
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
            r = await c.get(
                f"{BASE}/newsletter/admin/stats",
                headers={"x-admin-key": "test-secret-key"},
            )
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
            r = await c.get(
                f"{BASE}/newsletter/admin/subscribers",
                headers={"x-admin-key": "test-secret-key"},
            )
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
        "flash_title": "T",
        "flash_body": "T",
        "reflex_title": "T",
        "reflex_body": "T",
        "legal_title": "T",
        "legal_body": "T",
    }
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/admin/send-issue", json=issue_payload)
    assert r.status_code == 403


# ── Schedule ───────────────────────────────────────────────────────────────────

_SCHEDULE_PAYLOAD = [
    {
        "position": 1,
        "actu_title": "Faille critique OpenSSH — CVE-2025-1234",
        "actu_url": "https://www.bleepingcomputer.com/news/security/openssh-cve-2025-1234/",
        "actu_source": "BleepingComputer",
        "reflex": "Mettre à jour OpenSSH immédiatement",
    },
    {
        "position": 2,
        "actu_title": "Ransomware sur Change Healthcare",
        "actu_url": "https://techcrunch.com/2025/01/27/change-healthcare/",
        "actu_source": "TechCrunch",
        "reflex": "Activer la Double Authentification (MFA)",
    },
]


@pytest.mark.asyncio
async def test_get_schedule_returns_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/newsletter/schedule")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_admin_update_schedule_replaces_items():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(
                f"{BASE}/newsletter/admin/schedule",
                json=_SCHEDULE_PAYLOAD,
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert data[0]["position"] == 1
    assert data[0]["actu_title"] == "Faille critique OpenSSH — CVE-2025-1234"
    assert data[0]["actu_source"] == "BleepingComputer"
    assert "updated_at" in data[0]


@pytest.mark.asyncio
async def test_admin_update_schedule_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(f"{BASE}/newsletter/admin/schedule", json=_SCHEDULE_PAYLOAD)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_schedule_duplicate_positions_returns_422():
    bad_payload = [
        {**_SCHEDULE_PAYLOAD[0]},
        {**_SCHEDULE_PAYLOAD[0], "actu_title": "Duplicate"},  # same position=1
    ]
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(
                f"{BASE}/newsletter/admin/schedule",
                json=bad_payload,
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 422


# ── Send from schedule ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_send_from_schedule_no_items_returns_400():
    """Empty schedule → 400."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                f"{BASE}/newsletter/admin/send-from-schedule",
                json={"edition": 42},
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 400
    assert "planning" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_admin_send_from_schedule_with_items_returns_sent():
    """Populate schedule first, then send — returns count (0 if no active subscribers)."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.put(
                f"{BASE}/newsletter/admin/schedule",
                json=_SCHEDULE_PAYLOAD,
                headers={"x-admin-key": "test-secret-key"},
            )
            with patch("app.api.v1.endpoints.newsletter.send_newsletter_articles"):
                r = await c.post(
                    f"{BASE}/newsletter/admin/send-from-schedule",
                    json={"edition": 7},
                    headers={"x-admin-key": "test-secret-key"},
                )
    assert r.status_code == 200
    assert "sent" in r.json()
    assert r.json()["sent"] >= 0


@pytest.mark.asyncio
async def test_admin_send_from_schedule_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/newsletter/admin/send-from-schedule", json={"edition": 1})
    assert r.status_code == 403


# ── OG image ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_og_image_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/og-image?url=https://example.com")
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_admin_og_image_returns_null_on_exception():
    """SSRF block or network error → {"image_url": null}, not 500."""
    with _admin_settings():
        with patch(
            "app.api.v1.endpoints.newsletter.assert_no_ssrf",
            side_effect=Exception("blocked"),
        ):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.get(
                    f"{BASE}/newsletter/admin/og-image?url=https://example.com",
                    headers={"x-admin-key": "test-secret-key"},
                )
    assert r.status_code == 200
    assert r.json() == {"image_url": None}


@pytest.mark.asyncio
async def test_admin_og_image_returns_image_url_from_og_tag():
    """When page contains og:image, return the URL."""
    from unittest.mock import AsyncMock

    html = '<meta property="og:image" content="https://example.com/thumb.jpg" />'

    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.text = html
    mock_resp.url = "https://example.com"

    mock_http = MagicMock()
    mock_http.get = AsyncMock(return_value=mock_resp)

    mock_ctx = MagicMock()
    mock_ctx.__aenter__ = AsyncMock(return_value=mock_http)
    mock_ctx.__aexit__ = AsyncMock(return_value=False)

    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.assert_no_ssrf"):
            with patch(
                "app.api.v1.endpoints.newsletter.httpx.AsyncClient",
                return_value=mock_ctx,
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.get(
                        f"{BASE}/newsletter/admin/og-image?url=https://example.com",
                        headers={"x-admin-key": "test-secret-key"},
                    )
    assert r.status_code == 200
    assert r.json()["image_url"] == "https://example.com/thumb.jpg"


# ── Newsletter content ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_get_newsletter_content_returns_default():
    """No setting in DB → returns built-in default content."""
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                f"{BASE}/newsletter/admin/content",
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    data = r.json()
    assert "flash_title" in data
    assert "reflex_title" in data
    assert "legal_title" in data


@pytest.mark.asyncio
async def test_admin_update_newsletter_content_saves_and_returns():
    payload = {
        "flash_title": "Test Flash",
        "flash_body": "Corps du flash test.",
        "reflex_title": "Test Reflex",
        "reflex_body": "Corps du reflex test.",
        "legal_title": "Test Legal",
        "legal_body": "Corps legal test.",
    }
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(
                f"{BASE}/newsletter/admin/content",
                json=payload,
                headers={"x-admin-key": "test-secret-key"},
            )
    assert r.status_code == 200
    assert r.json()["flash_title"] == "Test Flash"
    assert r.json()["reflex_body"] == "Corps du reflex test."


@pytest.mark.asyncio
async def test_admin_get_newsletter_content_reads_from_db():
    """When AppSetting row exists in DB, GET parses and returns it (unit-level mock)."""
    import json as _json
    from unittest.mock import AsyncMock

    from app.api.v1.endpoints.newsletter import get_newsletter_content
    from app.models.app_setting import AppSetting

    content_data = {
        "flash_title": "Mocked Flash",
        "flash_body": "Mocked body.",
        "reflex_title": "Mocked Reflex",
        "reflex_body": "Mocked reflex body.",
        "legal_title": "Mocked Legal",
        "legal_body": "Mocked legal body.",
    }
    setting = AppSetting(
        key="newsletter_content", value_int=0, value_text=_json.dumps(content_data)
    )

    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=setting)

    result = await get_newsletter_content(db=mock_db)
    assert result.flash_title == "Mocked Flash"
    assert result.reflex_title == "Mocked Reflex"
