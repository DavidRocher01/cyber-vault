"""
Integration tests — /api/v1/admin/stats (coverage-focused)
Targets branches NOT exercised by test_admin_stats.py:
  - active_subscriptions counting (active vs non-active)
  - newsletter_subscribers (confirmed_at set vs None)
  - bookings_this_month + recent_bookings (confirmed join, cancelled excluded)
  - revenue_per_month aggregation from invoices
  - weekly_activity scans bucketing
  - POST /admin/awareness/sync-content (auth guard + all branches, mocked importer)
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.booking import Booking
from app.models.booking_slot import BookingSlot
from app.models.invoice import Invoice
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.plan import Plan
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.models.user import User

BASE = "/api/v1"
KEY = "test-secret-key"
HEADERS = {"x-admin-key": KEY}


def _admin_settings():
    mock = MagicMock()
    mock.ADMIN_API_KEY = KEY
    return patch("app.core.deps.settings", mock)


async def _get_stats() -> dict:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(f"{BASE}/admin/stats", headers=HEADERS)
    assert r.status_code == 200, r.text
    return r.json()


# ── active_subscriptions branch ─────────────────────────────────────────────────


async def test_stats_counts_only_active_subscriptions(db_session: AsyncSession):
    user = User(email="sub_owner@test.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    plan = Plan(
        name="pro",
        display_name="Pro",
        price_eur=2900,
        max_sites=3,
        scan_interval_days=7,
        tier_level=3,
    )
    db_session.add(plan)
    await db_session.flush()

    db_session.add_all(
        [
            Subscription(user_id=user.id, plan_id=plan.id, status="active"),
            Subscription(user_id=user.id, plan_id=plan.id, status="active"),
            Subscription(user_id=user.id, plan_id=plan.id, status="canceled"),
            Subscription(user_id=user.id, plan_id=plan.id, status="past_due"),
        ]
    )
    await db_session.commit()

    with _admin_settings():
        data = await _get_stats()

    assert data["active_subscriptions"] == 2


# ── newsletter_subscribers branch (confirmed_at) ────────────────────────────────


async def test_stats_counts_only_confirmed_newsletter(db_session: AsyncSession):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            NewsletterSubscriber(
                email="confirmed1@test.com",
                subscribed_at=now,
                confirmed_at=now,
                unsubscribe_token="u1",
            ),
            NewsletterSubscriber(
                email="confirmed2@test.com",
                subscribed_at=now,
                confirmed_at=now,
                unsubscribe_token="u2",
            ),
            NewsletterSubscriber(
                email="pending@test.com",
                subscribed_at=now,
                confirmed_at=None,
                unsubscribe_token="u3",
            ),
        ]
    )
    await db_session.commit()

    with _admin_settings():
        data = await _get_stats()

    assert data["newsletter_subscribers"] == 2


# ── bookings_this_month + recent_bookings branch ────────────────────────────────


async def test_stats_bookings_confirmed_join_and_excludes_cancelled(db_session: AsyncSession):
    now = datetime.now(UTC)
    slot = BookingSlot(date="2026-07-15", time="10:00", created_at=now)
    db_session.add(slot)
    await db_session.flush()

    db_session.add_all(
        [
            Booking(
                slot_id=slot.id,
                name="Alice",
                email="alice@test.com",
                need_type="audit-flash",
                status="confirmed",
                cancel_token="tok-a",
                created_at=now,
            ),
            Booking(
                slot_id=slot.id,
                name="Bob",
                email="bob@test.com",
                need_type="audit-flash",
                status="cancelled",
                cancel_token="tok-b",
                created_at=now,
            ),
        ]
    )
    await db_session.commit()

    with _admin_settings():
        data = await _get_stats()

    # Only the confirmed booking counts this month.
    assert data["bookings_this_month"] == 1
    assert len(data["recent_bookings"]) == 1
    rb = data["recent_bookings"][0]
    assert rb["name"] == "Alice"
    assert rb["date"] == "2026-07-15"
    assert rb["time"] == "10:00"
    assert "created_at" in rb


# ── revenue_per_month aggregation branch ────────────────────────────────────────


async def test_stats_revenue_aggregates_current_month_invoices(db_session: AsyncSession):
    now = datetime.now(UTC)
    db_session.add_all(
        [
            Invoice(
                invoice_number="F-0001",
                invoice_seq=1,
                invoice_year=now.year,
                type="subscription",
                client_name="C1",
                client_email="c1@test.com",
                description="Abonnement",
                amount_cents=2900,
                issue_date=now.date(),
                created_at=now,
            ),
            Invoice(
                invoice_number="F-0002",
                invoice_seq=2,
                invoice_year=now.year,
                type="audit",
                client_name="C2",
                client_email="c2@test.com",
                description="Audit",
                amount_cents=15000,
                issue_date=now.date(),
                created_at=now,
            ),
        ]
    )
    await db_session.commit()

    with _admin_settings():
        data = await _get_stats()

    # The last (current) month bucket should carry the summed cents.
    revenue = data["revenue_per_month"]
    assert len(revenue) == 6
    assert revenue[-1]["cents"] == 2900 + 15000
    # Earlier months stay at zero.
    assert sum(b["cents"] for b in revenue[:-1]) == 0


# ── weekly_activity scans bucketing branch ──────────────────────────────────────


async def test_stats_weekly_activity_counts_scans(db_session: AsyncSession):
    now = datetime.now(UTC)
    user = User(email="scan_owner@test.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    site = Site(user_id=user.id, url="https://example.com", name="Example")
    db_session.add(site)
    await db_session.flush()

    db_session.add_all(
        [
            Scan(site_id=site.id, status="done", created_at=now),
            Scan(site_id=site.id, status="failed", created_at=now),
        ]
    )
    await db_session.commit()

    with _admin_settings():
        data = await _get_stats()

    total_scans = sum(b["scans"] for b in data["weekly_activity"])
    assert total_scans == 2


# ── recent_contacts ordering/limit branch ───────────────────────────────────────


async def test_stats_recent_contacts_limited_to_five(db_session: AsyncSession):
    from app.models.contact_message import ContactMessage

    now = datetime.now(UTC)
    db_session.add_all(
        [
            ContactMessage(
                name=f"User{i}",
                email=f"u{i}@test.com",
                need_type="audit-flash",
                message="Message de test.",
                status="new",
                created_at=now,
            )
            for i in range(7)
        ]
    )
    await db_session.commit()

    with _admin_settings():
        data = await _get_stats()

    # new_contacts counts all 7, but recent_contacts is capped at 5.
    assert data["new_contacts"] == 7
    assert len(data["recent_contacts"]) == 5


# ── POST /admin/awareness/sync-content ──────────────────────────────────────────


async def test_sync_content_requires_admin_key():
    with _admin_settings():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(f"{BASE}/admin/awareness/sync-content")
    assert r.status_code == 403


async def test_sync_content_success():
    fake_summary = {"programs": 3, "modules": 12, "errors": []}
    with _admin_settings():
        with patch(
            "app.services.awareness_content_importer.import_from_directory",
            new=AsyncMock(return_value=fake_summary),
        ):
            with patch("app.api.v1.endpoints.admin_stats.Path") as mock_path:
                mock_path.return_value.parents.__getitem__.return_value = mock_path.return_value
                mock_path.return_value.__truediv__.return_value = mock_path.return_value
                mock_path.return_value.exists.return_value = True
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.post(f"{BASE}/admin/awareness/sync-content", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["programs"] == 3
    assert body["modules"] == 12
    assert body["errors"] == []


async def test_sync_content_missing_directory():
    with _admin_settings():
        with patch("app.api.v1.endpoints.admin_stats.Path") as mock_path:
            mock_path.return_value.parents.__getitem__.return_value = mock_path.return_value
            mock_path.return_value.__truediv__.return_value = mock_path.return_value
            mock_path.return_value.exists.return_value = False
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                r = await c.post(f"{BASE}/admin/awareness/sync-content", headers=HEADERS)
    assert r.status_code == 200
    assert "error" in r.json()


async def test_sync_content_importer_raises_returns_error():
    with _admin_settings():
        with patch(
            "app.services.awareness_content_importer.import_from_directory",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            with patch("app.api.v1.endpoints.admin_stats.Path") as mock_path:
                mock_path.return_value.parents.__getitem__.return_value = mock_path.return_value
                mock_path.return_value.__truediv__.return_value = mock_path.return_value
                mock_path.return_value.exists.return_value = True
                async with AsyncClient(
                    transport=ASGITransport(app=app), base_url="http://test"
                ) as c:
                    r = await c.post(f"{BASE}/admin/awareness/sync-content", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["error"] == "boom"
