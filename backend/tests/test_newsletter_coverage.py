"""
Coverage-lift tests — /api/v1/newsletter

Targets branches NOT exercised by test_newsletter.py:
- admin send-issue / send-from-schedule with *active* subscribers (count > 0, per-sub task)
- admin stats with a mix of active / pending / inactive subscribers
- admin subscribers pagination, ordering, and 422 on invalid limit
- get_newsletter_content when the DB row holds corrupted JSON -> default fallback
- admin content GET/PUT + subscribers refused (403) without the admin key
- update_schedule size validation (empty and > 6 -> 422)
- subscribe resend-confirmation rotates the confirmation token
- og-image redirect-follow branch, reverse-order og tag, relative-URL resolution,
  and the no-match -> {"image_url": None} branch
All email senders and outbound HTTP are mocked; nothing hits the network.
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import DEFAULT, AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import make_unsubscribe_token
from app.main import app
from app.models.newsletter_subscriber import NewsletterSubscriber

BASE = "/api/v1"


# ── Helpers ────────────────────────────────────────────────────────────────────


def _no_email():
    """Patch every newsletter email sender to a no-op mock (via DEFAULT)."""
    return patch.multiple(
        "app.api.v1.endpoints.newsletter",
        send_confirmation_email=DEFAULT,
        send_newsletter_welcome=DEFAULT,
        send_unsubscribe_confirmation=DEFAULT,
    )


@contextmanager
def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = "test-secret-key"
    mock.FRONTEND_URL = "http://localhost:4200"
    with (
        patch("app.api.v1.endpoints.newsletter.settings", mock),
        patch("app.core.deps.settings", mock),
    ):
        yield


def _session_local():
    import app.core.database as _db

    return _db.AsyncSessionLocal


async def _get_subscriber(email: str) -> NewsletterSubscriber | None:
    async with _session_local()() as db:
        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.email == email)
        )
        return result.scalar_one_or_none()


async def _seed_subscriber(
    email: str,
    *,
    is_active: bool,
    confirmed: bool,
    pending_token: bool = False,
) -> None:
    async with _session_local()() as db:
        sub = NewsletterSubscriber(
            email=email,
            subscribed_at=datetime.now(UTC),
            confirmed_at=datetime.now(UTC) if confirmed else None,
            is_active=is_active,
            confirmation_token=("tok-" + email) if pending_token else None,
            unsubscribe_token=make_unsubscribe_token(email),
        )
        db.add(sub)
        await db.commit()


_ADMIN_HEADERS = {"x-admin-key": "test-secret-key"}


# ── admin/send-issue with active subscribers (count > 0) ───────────────────────


@pytest.mark.asyncio
async def test_admin_send_issue_queues_one_task_per_active_subscriber():
    await _seed_subscriber("iss1@test.com", is_active=True, confirmed=True)
    await _seed_subscriber("iss2@test.com", is_active=True, confirmed=True)
    # An inactive subscriber must NOT receive the issue.
    await _seed_subscriber("issoff@test.com", is_active=False, confirmed=True)

    payload = {
        "edition": 3,
        "flash_title": "F",
        "flash_body": "FB",
        "reflex_title": "R",
        "reflex_body": "RB",
        "legal_title": "L",
        "legal_body": "LB",
    }
    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.send_newsletter_issue") as mock_send:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(
                    f"{BASE}/newsletter/admin/send-issue",
                    json=payload,
                    headers=_ADMIN_HEADERS,
                )
    assert r.status_code == 200
    assert r.json()["sent"] == 2
    assert mock_send.call_count == 2
    # Edition number is forwarded to the sender.
    assert mock_send.call_args_list[0].args[2] == 3


# ── admin/send-from-schedule with active subscribers (count > 0) ───────────────


@pytest.mark.asyncio
async def test_admin_send_from_schedule_queues_per_active_subscriber():
    schedule = [
        {
            "position": 1,
            "actu_title": "Faille OpenSSH",
            "actu_url": "https://example.com/openssh",
            "actu_source": "BleepingComputer",
            "reflex": "Mettre à jour",
        }
    ]
    await _seed_subscriber("sched1@test.com", is_active=True, confirmed=True)
    await _seed_subscriber("sched2@test.com", is_active=True, confirmed=True)
    await _seed_subscriber("schedoff@test.com", is_active=False, confirmed=True)

    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.put(
                f"{BASE}/newsletter/admin/schedule",
                json=schedule,
                headers=_ADMIN_HEADERS,
            )
            with patch("app.api.v1.endpoints.newsletter.send_newsletter_articles") as mock_send:
                r = await c.post(
                    f"{BASE}/newsletter/admin/send-from-schedule",
                    json={"edition": 9},
                    headers=_ADMIN_HEADERS,
                )
    assert r.status_code == 200
    assert r.json()["sent"] == 2
    assert mock_send.call_count == 2
    # articles list carries the single scheduled item.
    articles_arg = mock_send.call_args_list[0].args[3]
    assert len(articles_arg) == 1
    assert articles_arg[0]["actu_title"] == "Faille OpenSSH"


# ── admin/stats counts across mixed states ─────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_stats_counts_active_pending_and_inactive():
    await _seed_subscriber("act@test.com", is_active=True, confirmed=True)
    await _seed_subscriber("pend@test.com", is_active=False, confirmed=False, pending_token=True)
    # Inactive with no confirmation token (unsubscribed) — neither active nor pending.
    await _seed_subscriber("gone@test.com", is_active=False, confirmed=True)

    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/stats", headers=_ADMIN_HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert data["active"] == 1
    assert data["pending_confirmation"] == 1


# ── admin/subscribers pagination + ordering + validation ───────────────────────


@pytest.mark.asyncio
async def test_admin_subscribers_pagination_and_ordering():
    # subscribed_at ordered desc → most recent first.
    async with _session_local()() as db:
        for i in range(3):
            db.add(
                NewsletterSubscriber(
                    email=f"page{i}@test.com",
                    subscribed_at=datetime(2026, 1, i + 1, tzinfo=UTC),
                    is_active=True,
                    unsubscribe_token=make_unsubscribe_token(f"page{i}@test.com"),
                )
            )
        await db.commit()

    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r_all = await c.get(f"{BASE}/newsletter/admin/subscribers", headers=_ADMIN_HEADERS)
            r_page = await c.get(
                f"{BASE}/newsletter/admin/subscribers?skip=1&limit=1",
                headers=_ADMIN_HEADERS,
            )
    assert r_all.status_code == 200
    emails = [s["email"] for s in r_all.json()]
    assert emails == ["page2@test.com", "page1@test.com", "page0@test.com"]

    assert r_page.status_code == 200
    page = r_page.json()
    assert len(page) == 1
    assert page[0]["email"] == "page1@test.com"


@pytest.mark.asyncio
async def test_admin_subscribers_invalid_limit_returns_422():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(
                f"{BASE}/newsletter/admin/subscribers?limit=9999",
                headers=_ADMIN_HEADERS,
            )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_subscribers_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get(f"{BASE}/newsletter/admin/subscribers")
    assert r.status_code == 403


# ── get content — corrupted JSON falls back to default ─────────────────────────


@pytest.mark.asyncio
async def test_admin_get_newsletter_content_corrupt_json_returns_default():
    """A row whose value_text is not valid JSON must not 500 — default is returned."""
    from app.api.v1.endpoints.newsletter import _DEFAULT_CONTENT, get_newsletter_content
    from app.models.app_setting import AppSetting

    setting = AppSetting(key="newsletter_content", value_int=0, value_text="{not-valid-json")
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=setting)

    result = await get_newsletter_content(db=mock_db)
    assert result.flash_title == _DEFAULT_CONTENT.flash_title


@pytest.mark.asyncio
async def test_admin_get_newsletter_content_empty_value_text_returns_default():
    """A row that exists but has an empty value_text → default (short-circuit branch)."""
    from app.api.v1.endpoints.newsletter import _DEFAULT_CONTENT, get_newsletter_content
    from app.models.app_setting import AppSetting

    setting = AppSetting(key="newsletter_content", value_int=0, value_text="")
    mock_db = MagicMock()
    mock_db.get = AsyncMock(return_value=setting)

    result = await get_newsletter_content(db=mock_db)
    assert result.legal_title == _DEFAULT_CONTENT.legal_title


@pytest.mark.asyncio
async def test_admin_content_no_key_returns_403():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r_get = await c.get(f"{BASE}/newsletter/admin/content")
            r_put = await c.put(
                f"{BASE}/newsletter/admin/content",
                json={
                    "flash_title": "a",
                    "flash_body": "b",
                    "reflex_title": "c",
                    "reflex_body": "d",
                    "legal_title": "e",
                    "legal_body": "f",
                },
            )
    assert r_get.status_code == 403
    assert r_put.status_code == 403


@pytest.mark.asyncio
async def test_admin_update_content_updates_existing_row():
    """Second PUT hits the 'setting is not None' branch (update, not insert)."""
    first = {
        "flash_title": "v1",
        "flash_body": "b1",
        "reflex_title": "r1",
        "reflex_body": "rb1",
        "legal_title": "l1",
        "legal_body": "lb1",
    }
    second = {**first, "flash_title": "v2"}
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.put(f"{BASE}/newsletter/admin/content", json=first, headers=_ADMIN_HEADERS)
            r2 = await c.put(
                f"{BASE}/newsletter/admin/content", json=second, headers=_ADMIN_HEADERS
            )
            r_get = await c.get(f"{BASE}/newsletter/admin/content", headers=_ADMIN_HEADERS)
    assert r2.status_code == 200
    assert r_get.json()["flash_title"] == "v2"


# ── update_schedule size validation ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_update_schedule_empty_list_returns_422():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(f"{BASE}/newsletter/admin/schedule", json=[], headers=_ADMIN_HEADERS)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_admin_update_schedule_too_many_items_returns_422():
    items = [
        {
            "position": i,
            "actu_title": f"Titre {i}",
            "actu_url": f"https://example.com/{i}",
            "actu_source": "Src",
            "reflex": "Reflex",
        }
        for i in range(1, 8)  # 7 items > 6
    ]
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.put(f"{BASE}/newsletter/admin/schedule", json=items, headers=_ADMIN_HEADERS)
    assert r.status_code == 422


# ── subscribe: pending resubscribe rotates the confirmation token ──────────────


@pytest.mark.asyncio
async def test_subscribe_pending_rotates_confirmation_token():
    with _no_email() as mocks:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.post(f"{BASE}/newsletter/subscribe", json={"email": "rot@test.com"})
            first_token = (await _get_subscriber("rot@test.com")).confirmation_token
            mocks["send_confirmation_email"].reset_mock()
            r = await c.post(f"{BASE}/newsletter/subscribe", json={"email": "rot@test.com"})
    assert r.status_code == 201
    second_token = (await _get_subscriber("rot@test.com")).confirmation_token
    assert second_token is not None
    assert second_token != first_token
    mocks["send_confirmation_email"].assert_called_once()


# ── og-image extra branches ────────────────────────────────────────────────────


def _mock_httpx_client(resp):
    """Build an async-context-manager mock whose .get() returns resp."""
    http = MagicMock()
    http.get = AsyncMock(return_value=resp)
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=http)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


@pytest.mark.asyncio
async def test_admin_og_image_no_meta_tag_returns_none():
    resp = MagicMock()
    resp.is_redirect = False
    resp.text = "<html><head><title>No og image here</title></head></html>"
    resp.url = "https://example.com"

    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.assert_no_ssrf"):
            with patch(
                "app.api.v1.endpoints.newsletter.httpx.AsyncClient",
                return_value=_mock_httpx_client(resp),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.get(
                        f"{BASE}/newsletter/admin/og-image?url=https://example.com",
                        headers=_ADMIN_HEADERS,
                    )
    assert r.status_code == 200
    assert r.json() == {"image_url": None}


@pytest.mark.asyncio
async def test_admin_og_image_reverse_order_and_relative_root_url():
    """content=... before property=og:image, and a root-relative image path."""
    html = '<meta content="/static/thumb.png" property="og:image">'
    resp = MagicMock()
    resp.is_redirect = False
    resp.text = html
    resp.url = "https://cdn.example.com/article"

    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.assert_no_ssrf"):
            with patch(
                "app.api.v1.endpoints.newsletter.httpx.AsyncClient",
                return_value=_mock_httpx_client(resp),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.get(
                        f"{BASE}/newsletter/admin/og-image?url=https://cdn.example.com/article",
                        headers=_ADMIN_HEADERS,
                    )
    assert r.status_code == 200
    assert r.json()["image_url"] == "https://cdn.example.com/static/thumb.png"


@pytest.mark.asyncio
async def test_admin_og_image_protocol_relative_url():
    """A // protocol-relative og:image gets an https: prefix."""
    html = '<meta property="og:image" content="//cdn.example.com/pic.jpg" />'
    resp = MagicMock()
    resp.is_redirect = False
    resp.text = html
    resp.url = "https://example.com/page"

    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.assert_no_ssrf"):
            with patch(
                "app.api.v1.endpoints.newsletter.httpx.AsyncClient",
                return_value=_mock_httpx_client(resp),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.get(
                        f"{BASE}/newsletter/admin/og-image?url=https://example.com/page",
                        headers=_ADMIN_HEADERS,
                    )
    assert r.status_code == 200
    assert r.json()["image_url"] == "https://cdn.example.com/pic.jpg"


@pytest.mark.asyncio
async def test_admin_og_image_follows_redirect():
    """First response is a redirect -> a second client fetches the location."""
    redirect_resp = MagicMock()
    redirect_resp.is_redirect = True
    redirect_resp.headers = {"location": "https://final.example.com/real"}

    final_resp = MagicMock()
    final_resp.is_redirect = False
    final_resp.text = '<meta property="og:image" content="https://final.example.com/i.png">'
    final_resp.url = "https://final.example.com/real"

    clients = [_mock_httpx_client(redirect_resp), _mock_httpx_client(final_resp)]

    with _admin_settings():
        with patch("app.api.v1.endpoints.newsletter.assert_no_ssrf"):
            with patch(
                "app.api.v1.endpoints.newsletter.httpx.AsyncClient",
                side_effect=lambda *a, **k: clients.pop(0),
            ):
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.get(
                        f"{BASE}/newsletter/admin/og-image?url=https://example.com/start",
                        headers=_ADMIN_HEADERS,
                    )
    assert r.status_code == 200
    assert r.json()["image_url"] == "https://final.example.com/i.png"
