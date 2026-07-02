"""
Integration tests — /api/v1/webhooks/stripe (the "money path").

Verifies the Stripe webhook handler mutates the Subscription table correctly for
each lifecycle event. The real Stripe signature check is NEVER exercised here:
`construct_webhook_event` is mocked to return a fabricated (already-trusted) event,
and `stripe.Subscription.retrieve` (called via asyncio.to_thread inside the
checkout handler) is mocked to avoid any network call.

Covered:
- checkout.session.completed  → subscription created + active + right plan + Stripe ids stored
- checkout.session.completed  → existing subscription upserted (no duplicate)
- customer.subscription.updated → plan status synced (e.g. past_due)
- customer.subscription.deleted → status becomes "canceled"
- invalid signature            → 400 AND no DB mutation (security invariant)
- unknown event type           → 200 with no effect (robustness/idempotence)
- duplicate event id           → processed once (idempotence)
"""

from unittest.mock import MagicMock, patch

import pytest
import stripe
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.main import app
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User

BASE = "/api/v1"
WEBHOOK_URL = f"{BASE}/webhooks/stripe"

# Fixed epoch timestamps for deterministic period start/end.
PERIOD_START = 1_700_000_000
PERIOD_END = 1_702_592_000


# ── Seed helpers ──────────────────────────────────────────────────────────────


async def _seed_plan(
    name: str = "pro",
    stripe_price_id: str = "price_pro_123",
    tier_level: int = 3,
) -> int:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        plan = Plan(
            name=name,
            display_name=name.capitalize(),
            price_eur=2900,
            max_sites=5,
            scan_interval_days=7,
            tier_level=tier_level,
            stripe_price_id=stripe_price_id,
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan.id


async def _seed_user(email: str) -> int:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = User(email=email, hashed_password="x")
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user.id


async def _seed_subscription(
    user_id: int,
    plan_id: int,
    stripe_subscription_id: str = "sub_existing",
    stripe_customer_id: str = "cus_existing",
    status: str = "active",
) -> int:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            status=status,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub.id


async def _get_sub_for_user(user_id: int) -> Subscription | None:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
        return result.scalar_one_or_none()


async def _count_subscriptions() -> int:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Subscription))
        return len(result.scalars().all())


def _checkout_event(
    email: str,
    customer_id: str = "cus_new",
    subscription_id: str = "sub_new",
    event_id: str = "evt_checkout_1",
) -> dict:
    return {
        "id": event_id,
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": customer_id,
                "subscription": subscription_id,
                "customer_details": {"email": email},
                "metadata": {},
            }
        },
    }


def _stripe_sub_retrieve(price_id: str = "price_pro_123") -> dict:
    """Fake payload returned by stripe.Subscription.retrieve."""
    return {
        "items": {"data": [{"price": {"id": price_id}}]},
        "current_period_start": PERIOD_START,
        "current_period_end": PERIOD_END,
    }


def _subscription_lifecycle_event(
    event_type: str,
    subscription_id: str,
    status: str,
    event_id: str,
) -> dict:
    return {
        "id": event_id,
        "type": event_type,
        "data": {
            "object": {
                "id": subscription_id,
                "status": status,
                "current_period_end": PERIOD_END,
            }
        },
    }


# ── checkout.session.completed ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_completed_creates_active_subscription():
    plan_id = await _seed_plan(stripe_price_id="price_pro_active")
    await _seed_user("money1@test.com")

    event = _checkout_event("money1@test.com", customer_id="cus_A", subscription_id="sub_A")

    with (
        patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            return_value=event,
        ),
        patch(
            "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
            new=MagicMock(return_value=_stripe_sub_retrieve("price_pro_active")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "whatever"})

    assert r.status_code == 200

    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == "money1@test.com"))).scalar_one()
        sub = (
            await db.execute(select(Subscription).where(Subscription.user_id == user.id))
        ).scalar_one()

    assert sub.status == "active"
    assert sub.plan_id == plan_id
    assert sub.stripe_customer_id == "cus_A"
    assert sub.stripe_subscription_id == "sub_A"
    assert sub.current_period_start is not None
    assert sub.current_period_end is not None


@pytest.mark.asyncio
async def test_checkout_completed_upserts_existing_subscription():
    """Existing sub for the user is updated in place (no duplicate row)."""
    plan_id = await _seed_plan(stripe_price_id="price_pro_upsert")
    user_id = await _seed_user("money2@test.com")
    # Pre-existing sub in a different (canceled) state with stale Stripe ids.
    await _seed_subscription(
        user_id,
        plan_id,
        stripe_subscription_id="sub_stale",
        stripe_customer_id="cus_stale",
        status="canceled",
    )

    event = _checkout_event("money2@test.com", customer_id="cus_fresh", subscription_id="sub_fresh")

    with (
        patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            return_value=event,
        ),
        patch(
            "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
            new=MagicMock(return_value=_stripe_sub_retrieve("price_pro_upsert")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert r.status_code == 200
    assert await _count_subscriptions() == 1

    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.status == "active"
    assert sub.stripe_customer_id == "cus_fresh"
    assert sub.stripe_subscription_id == "sub_fresh"


@pytest.mark.asyncio
async def test_checkout_completed_unknown_price_does_not_activate():
    """No matching plan for the Stripe price_id → no subscription is created."""
    await _seed_plan(stripe_price_id="price_known")
    await _seed_user("money3@test.com")

    event = _checkout_event("money3@test.com")

    with (
        patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            return_value=event,
        ),
        patch(
            "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
            new=MagicMock(return_value=_stripe_sub_retrieve("price_UNMAPPED")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    # Endpoint still 200 (event acknowledged), but nothing activated.
    assert r.status_code == 200
    assert await _count_subscriptions() == 0


# ── customer.subscription.updated ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subscription_updated_syncs_status():
    plan_id = await _seed_plan(stripe_price_id="price_upd")
    user_id = await _seed_user("money4@test.com")
    await _seed_subscription(user_id, plan_id, stripe_subscription_id="sub_upd", status="active")

    event = _subscription_lifecycle_event(
        "customer.subscription.updated",
        subscription_id="sub_upd",
        status="past_due",
        event_id="evt_upd_1",
    )

    with patch(
        "app.api.v1.endpoints.webhooks.construct_webhook_event",
        return_value=event,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert r.status_code == 200
    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.status == "past_due"
    assert sub.current_period_end is not None


@pytest.mark.asyncio
async def test_subscription_updated_unknown_id_is_noop():
    """Update for a Stripe sub id not in our DB → no crash, no row mutated."""
    plan_id = await _seed_plan(stripe_price_id="price_noop")
    user_id = await _seed_user("money5@test.com")
    await _seed_subscription(user_id, plan_id, stripe_subscription_id="sub_ours", status="active")

    event = _subscription_lifecycle_event(
        "customer.subscription.updated",
        subscription_id="sub_someone_else",
        status="canceled",
        event_id="evt_upd_noop",
    )

    with patch(
        "app.api.v1.endpoints.webhooks.construct_webhook_event",
        return_value=event,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert r.status_code == 200
    # Our subscription is untouched.
    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.status == "active"


# ── customer.subscription.deleted ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subscription_deleted_marks_canceled():
    plan_id = await _seed_plan(stripe_price_id="price_del")
    user_id = await _seed_user("money6@test.com")
    await _seed_subscription(user_id, plan_id, stripe_subscription_id="sub_del", status="active")

    event = _subscription_lifecycle_event(
        "customer.subscription.deleted",
        subscription_id="sub_del",
        status="canceled",
        event_id="evt_del_1",
    )

    with patch(
        "app.api.v1.endpoints.webhooks.construct_webhook_event",
        return_value=event,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert r.status_code == 200
    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.status == "canceled"


# ── Security invariant: invalid signature ─────────────────────────────────────


@pytest.mark.asyncio
async def test_invalid_signature_returns_400_and_no_db_mutation():
    """
    If construct_webhook_event raises SignatureVerificationError, the endpoint
    must return 400 and the subscription in DB must be left untouched.
    This is the core security invariant: a forged/unsigned payload can never
    activate or alter a subscription.
    """
    plan_id = await _seed_plan(stripe_price_id="price_sig")
    user_id = await _seed_user("money7@test.com")
    await _seed_subscription(user_id, plan_id, stripe_subscription_id="sub_sig", status="active")

    def _raise(*_a, **_k):
        raise stripe.SignatureVerificationError("bad sig", "sig-header")

    with patch(
        "app.api.v1.endpoints.webhooks.construct_webhook_event",
        side_effect=_raise,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(
                WEBHOOK_URL,
                content=b'{"type":"checkout.session.completed"}',
                headers={"stripe-signature": "forged"},
            )

    assert r.status_code == 400
    # DB unchanged.
    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.status == "active"
    assert sub.stripe_subscription_id == "sub_sig"


@pytest.mark.asyncio
async def test_malformed_payload_returns_400():
    """Any other exception from construct_webhook_event → 400 Invalid payload."""

    def _raise(*_a, **_k):
        raise ValueError("not json")

    with patch(
        "app.api.v1.endpoints.webhooks.construct_webhook_event",
        side_effect=_raise,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"garbage", headers={"stripe-signature": "x"})

    assert r.status_code == 400
    assert await _count_subscriptions() == 0


# ── Robustness: unknown event type ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_event_type_is_acknowledged_without_effect():
    plan_id = await _seed_plan(stripe_price_id="price_unknown")
    user_id = await _seed_user("money8@test.com")
    await _seed_subscription(
        user_id, plan_id, stripe_subscription_id="sub_unknown", status="active"
    )

    event = {
        "id": "evt_unknown_1",
        "type": "customer.updated",  # not handled by the endpoint
        "data": {"object": {"id": "cus_x"}},
    }

    with patch(
        "app.api.v1.endpoints.webhooks.construct_webhook_event",
        return_value=event,
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})

    assert r.status_code == 200
    # No mutation.
    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.status == "active"


# ── Idempotence: duplicate event id ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_duplicate_event_id_processed_once():
    """
    Replaying the same event id must not double-apply. The second delivery of a
    checkout.session.completed with the same id must be a no-op (still 200).
    """
    plan_a = await _seed_plan(name="plan_a", stripe_price_id="price_dup_a", tier_level=3)
    plan_b = await _seed_plan(name="plan_b", stripe_price_id="price_dup_b", tier_level=4)
    user_id = await _seed_user("money9@test.com")

    event = _checkout_event(
        "money9@test.com",
        customer_id="cus_dup",
        subscription_id="sub_dup",
        event_id="evt_dup_same",
    )

    # First delivery → maps to plan_a.
    with (
        patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            return_value=event,
        ),
        patch(
            "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
            new=MagicMock(return_value=_stripe_sub_retrieve("price_dup_a")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r1 = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})
    assert r1.status_code == 200

    # Second delivery of the SAME event id, but now the (would-be) price maps to
    # plan_b. Because the event id was already processed, the handler must skip
    # and leave the subscription on plan_a.
    with (
        patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            return_value=event,
        ),
        patch(
            "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
            new=MagicMock(return_value=_stripe_sub_retrieve("price_dup_b")),
        ),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r2 = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "sig"})
    assert r2.status_code == 200

    assert await _count_subscriptions() == 1
    sub = await _get_sub_for_user(user_id)
    assert sub is not None
    assert sub.plan_id == plan_a  # unchanged by the replay
