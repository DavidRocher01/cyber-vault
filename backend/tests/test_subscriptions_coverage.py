"""
Coverage tests — /api/v1/subscriptions PRODUCTION (Stripe) paths.

The existing test_subscriptions.py covers dev-mode + free-plan + 404/400/401
branches. This file targets the *paid Stripe* branches that only run when
DEV_MODE is False and the plan has a stripe_price_id:

- checkout: reuse existing stripe_customer_id vs. create a new Stripe customer
- checkout: Stripe raising an error is surfaced (500)
- portal: real Stripe billing-portal session for an active sub with a customer id
- portal: active sub WITHOUT a customer id → 404
- portal: no active subscription → 404
- extra-sites: real Stripe checkout when the add-on price id is configured
- extra-sites: add-on not configured → 400

Every Stripe call is mocked — no network, deterministic. Stripe functions are
invoked through asyncio.to_thread in the endpoint, so we patch the
`stripe_service` symbols referenced inside the endpoint module.
"""

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User

BASE = "/api/v1"
SUB_MODULE = "app.api.v1.endpoints.subscriptions"


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _headers(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _user_id(email: str) -> int:
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        return (await db.execute(select(User).where(User.email == email))).scalar_one().id


async def _seed_paid_plan(name: str, stripe_price_id: str = "price_paid_123") -> int:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        plan = Plan(
            name=name,
            display_name=name.capitalize(),
            price_eur=2900,
            max_sites=5,
            scan_interval_days=7,
            tier_level=3,
            stripe_price_id=stripe_price_id,
            is_active=True,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan.id


async def _seed_subscription(
    user_id: int,
    plan_id: int,
    *,
    stripe_customer_id: str = "cus_existing",
    status: str = "active",
) -> int:
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id="sub_existing",
            status=status,
        )
        db.add(sub)
        await db.commit()
        await db.refresh(sub)
        return sub.id


# ── checkout: paid Stripe flow ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_paid_creates_new_customer_when_none():
    """No existing sub → endpoint creates a Stripe customer, then a checkout session."""
    plan_id = await _seed_paid_plan("pro_new_cust", stripe_price_id="price_new_cust")

    create_customer = MagicMock(return_value="cus_created")
    create_session = MagicMock(return_value="https://stripe.test/checkout/new")

    with (
        patch(f"{SUB_MODULE}.DEV_MODE", False),
        patch(f"{SUB_MODULE}.stripe_service.create_customer", create_customer),
        patch(f"{SUB_MODULE}.stripe_service.create_checkout_session", create_session),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "paid_new@test.com")
            r = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)

    assert r.status_code == 200
    assert r.json()["checkout_url"] == "https://stripe.test/checkout/new"
    # A fresh customer had to be created (no existing sub with a customer id).
    create_customer.assert_called_once_with("paid_new@test.com")
    # And the checkout session used the freshly created customer + plan price.
    _, kwargs = create_session.call_args
    assert kwargs["customer_id"] == "cus_created"
    assert kwargs["price_id"] == "price_new_cust"


@pytest.mark.asyncio
async def test_checkout_paid_reuses_existing_customer_id():
    """Existing sub already has a stripe_customer_id → no new customer is created."""
    plan_id = await _seed_paid_plan("pro_reuse", stripe_price_id="price_reuse")

    create_customer = MagicMock(return_value="cus_should_not_be_used")
    create_session = MagicMock(return_value="https://stripe.test/checkout/reuse")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "paid_reuse@test.com")
        uid = await _user_id("paid_reuse@test.com")
        await _seed_subscription(
            uid, plan_id, stripe_customer_id="cus_already_here", status="active"
        )

        with (
            patch(f"{SUB_MODULE}.DEV_MODE", False),
            patch(f"{SUB_MODULE}.stripe_service.create_customer", create_customer),
            patch(f"{SUB_MODULE}.stripe_service.create_checkout_session", create_session),
        ):
            r = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)

    assert r.status_code == 200
    assert r.json()["checkout_url"] == "https://stripe.test/checkout/reuse"
    create_customer.assert_not_called()
    _, kwargs = create_session.call_args
    assert kwargs["customer_id"] == "cus_already_here"


@pytest.mark.asyncio
async def test_checkout_paid_existing_sub_without_customer_id_creates_customer():
    """Existing sub whose stripe_customer_id is empty → falls back to creating one."""
    plan_id = await _seed_paid_plan("pro_empty_cust", stripe_price_id="price_empty_cust")

    create_customer = MagicMock(return_value="cus_fresh_fallback")
    create_session = MagicMock(return_value="https://stripe.test/checkout/fallback")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "paid_empty@test.com")
        uid = await _user_id("paid_empty@test.com")
        # Empty string customer id is falsy → the else branch (create_customer) runs.
        await _seed_subscription(uid, plan_id, stripe_customer_id="", status="active")

        with (
            patch(f"{SUB_MODULE}.DEV_MODE", False),
            patch(f"{SUB_MODULE}.stripe_service.create_customer", create_customer),
            patch(f"{SUB_MODULE}.stripe_service.create_checkout_session", create_session),
        ):
            r = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)

    assert r.status_code == 200
    create_customer.assert_called_once_with("paid_empty@test.com")
    _, kwargs = create_session.call_args
    assert kwargs["customer_id"] == "cus_fresh_fallback"


@pytest.mark.asyncio
async def test_checkout_paid_stripe_error_bubbles_up():
    """If Stripe raises while creating the checkout session, the request fails (500)."""
    plan_id = await _seed_paid_plan("pro_boom", stripe_price_id="price_boom")

    def _boom(*_a, **_k):
        raise RuntimeError("stripe is down")

    with (
        patch(f"{SUB_MODULE}.DEV_MODE", False),
        patch(f"{SUB_MODULE}.stripe_service.create_customer", MagicMock(return_value="cus_x")),
        patch(f"{SUB_MODULE}.stripe_service.create_checkout_session", MagicMock(side_effect=_boom)),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
        ) as c:
            h = await _headers(c, "paid_boom@test.com")
            r = await c.post(f"{BASE}/subscriptions/checkout/{plan_id}", headers=h)

    assert r.status_code == 500


# ── portal: real Stripe billing-portal path ───────────────────────────────────


@pytest.mark.asyncio
async def test_portal_active_sub_returns_stripe_portal_url():
    """Non-dev mode + active sub with a customer id → real billing-portal URL."""
    plan_id = await _seed_paid_plan("pro_portal", stripe_price_id="price_portal")

    create_portal = MagicMock(return_value="https://stripe.test/portal/session")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "portal_ok@test.com")
        uid = await _user_id("portal_ok@test.com")
        await _seed_subscription(uid, plan_id, stripe_customer_id="cus_portal", status="active")

        with (
            patch(f"{SUB_MODULE}.DEV_MODE", False),
            patch(f"{SUB_MODULE}.stripe_service.create_billing_portal_session", create_portal),
        ):
            r = await c.get(f"{BASE}/subscriptions/portal", headers=h)

    assert r.status_code == 200
    assert r.json()["checkout_url"] == "https://stripe.test/portal/session"
    _, kwargs = create_portal.call_args
    assert kwargs["customer_id"] == "cus_portal"


@pytest.mark.asyncio
async def test_portal_no_active_subscription_returns_404():
    """Non-dev mode + no active subscription → 404."""
    with patch(f"{SUB_MODULE}.DEV_MODE", False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            h = await _headers(c, "portal_none@test.com")
            r = await c.get(f"{BASE}/subscriptions/portal", headers=h)

    assert r.status_code == 404
    assert "No active subscription" in r.json()["detail"]


@pytest.mark.asyncio
async def test_portal_active_sub_without_customer_id_returns_404():
    """Active sub but empty stripe_customer_id → cannot open portal → 404."""
    plan_id = await _seed_paid_plan("pro_portal_nocust", stripe_price_id="price_portal_nocust")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "portal_nocust@test.com")
        uid = await _user_id("portal_nocust@test.com")
        await _seed_subscription(uid, plan_id, stripe_customer_id="", status="active")

        with patch(f"{SUB_MODULE}.DEV_MODE", False):
            r = await c.get(f"{BASE}/subscriptions/portal", headers=h)

    assert r.status_code == 404


# ── extra-sites: real Stripe path ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_purchase_extra_sites_not_configured_returns_400():
    """Non-dev mode + no add-on price id configured → 400."""
    plan_id = await _seed_paid_plan("pro_addon_unconf", stripe_price_id="price_addon_unconf")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "addon_unconf@test.com")
        uid = await _user_id("addon_unconf@test.com")
        await _seed_subscription(uid, plan_id, stripe_customer_id="cus_addon", status="active")

        with (
            patch(f"{SUB_MODULE}.DEV_MODE", False),
            patch(f"{SUB_MODULE}.settings.ADDON_EXTRA_SITES_STRIPE_PRICE_ID", ""),
        ):
            r = await c.post(f"{BASE}/subscriptions/addons/extra-sites/checkout", headers=h)

    assert r.status_code == 400
    assert "non configuré" in r.json()["detail"]


@pytest.mark.asyncio
async def test_purchase_extra_sites_configured_returns_stripe_url():
    """Non-dev mode + configured add-on price id → real Stripe checkout URL."""
    plan_id = await _seed_paid_plan("pro_addon_ok", stripe_price_id="price_addon_ok")

    create_session = MagicMock(return_value="https://stripe.test/checkout/addon")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        h = await _headers(c, "addon_ok@test.com")
        uid = await _user_id("addon_ok@test.com")
        await _seed_subscription(uid, plan_id, stripe_customer_id="cus_addon_ok", status="active")

        with (
            patch(f"{SUB_MODULE}.DEV_MODE", False),
            patch(f"{SUB_MODULE}.settings.ADDON_EXTRA_SITES_STRIPE_PRICE_ID", "price_addon_pack"),
            patch(f"{SUB_MODULE}.stripe_service.create_checkout_session", create_session),
        ):
            r = await c.post(f"{BASE}/subscriptions/addons/extra-sites/checkout", headers=h)

    assert r.status_code == 200
    assert r.json()["checkout_url"] == "https://stripe.test/checkout/addon"
    _, kwargs = create_session.call_args
    assert kwargs["customer_id"] == "cus_addon_ok"
    assert kwargs["price_id"] == "price_addon_pack"
    assert kwargs["metadata"]["addon_type"] == "extra_sites"
