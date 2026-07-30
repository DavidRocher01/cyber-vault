"""
Integration tests — Stripe webhook endpoint.
Covers: checkout.session.completed, customer.subscription.updated,
        invalid signature, missing customer data.
"""

import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

BASE = "/api/v1"

WEBHOOK_URL = f"{BASE}/webhooks/stripe"

# ── Helpers ────────────────────────────────────────────────────────────────────

_event_counter = 0


def _make_event(event_type: str, data: dict) -> dict:
    global _event_counter
    _event_counter += 1
    return {
        "id": f"evt_test_{_event_counter}",
        "type": event_type,
        "data": {"object": data},
    }


def _stripe_sub_mock(
    price_id: str = "price_test_123",
    period_start: int = 1700000000,
    period_end: int = 1702678400,
) -> MagicMock:
    """Return a minimal fake stripe.Subscription.retrieve() result."""
    mock = MagicMock()
    mock.__getitem__ = lambda self, key: {
        "items": {"data": [{"price": {"id": price_id}}]},
        "current_period_start": period_start,
        "current_period_end": period_end,
    }[key]
    return mock


# ── Invalid signature ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stripe_webhook_invalid_signature_returns_400():
    import stripe

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            side_effect=stripe.SignatureVerificationError("bad sig", "header"),
        ):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "bad"})
    assert r.status_code == 400
    assert "signature" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_stripe_webhook_generic_parse_error_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch(
            "app.api.v1.endpoints.webhooks.construct_webhook_event",
            side_effect=Exception("parse error"),
        ):
            r = await c.post(WEBHOOK_URL, content=b"bad", headers={"stripe-signature": "x"})
    assert r.status_code == 400


# ── checkout.session.completed ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_completed_creates_subscription():
    """After checkout.session.completed, a subscription row must exist for the user."""
    from sqlalchemy import select

    import app.core.database as db_mod
    from app.models.plan import Plan
    from app.models.subscription import Subscription

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Register user
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "wh1@test.com", "password": "StrongPass123!"},
        )

        # Seed a plan with a known stripe_price_id
        async with db_mod.AsyncSessionLocal() as session:
            plan = Plan(
                name="starter",
                display_name="Starter",
                price_eur=990,
                stripe_price_id="price_wh_test",
                max_sites=1,
                scan_interval_days=30,
                tier_level=2,
                is_active=True,
            )
            session.add(plan)
            await session.commit()
            plan_id = plan.id

        event = _make_event(
            "checkout.session.completed",
            {
                "customer": "cus_test_123",
                "subscription": "sub_test_456",
                "customer_details": {"email": "wh1@test.com"},
            },
        )

        stripe_sub = {
            "items": {"data": [{"price": {"id": "price_wh_test"}}]},
            "current_period_start": 1700000000,
            "current_period_end": 1702678400,
        }

        with (
            patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event),
            patch(
                "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
                return_value=stripe_sub,
            ),
        ):
            r = await c.post(
                WEBHOOK_URL,
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mock"},
            )

        assert r.status_code == 200
        assert r.json()["status"] == "ok"

        # Check subscription exists
        async with db_mod.AsyncSessionLocal() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.plan_id == plan_id)
            )
            sub = result.scalar_one_or_none()
        assert sub is not None
        assert sub.status == "active"
        assert sub.stripe_customer_id == "cus_test_123"


@pytest.mark.asyncio
async def test_checkout_completed_unknown_price_id_ignored():
    """Si le price_id ne correspond à aucun plan, on ignore silencieusement."""
    event = _make_event(
        "checkout.session.completed",
        {
            "customer": "cus_unknown",
            "subscription": "sub_unknown",
            "customer_details": {"email": "wh2@test.com"},
        },
    )
    stripe_sub = {
        "items": {"data": [{"price": {"id": "price_does_not_exist"}}]},
        "current_period_start": 1700000000,
        "current_period_end": 1702678400,
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with (
            patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event),
            patch(
                "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
                return_value=stripe_sub,
            ),
        ):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_checkout_completed_missing_customer_ignored():
    """customer/subscription absents → traitement ignoré, pas d'erreur 500."""
    event = _make_event(
        "checkout.session.completed",
        {
            "customer_details": {"email": "wh3@test.com"},
            # customer and subscription intentionally missing
        },
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})
    assert r.status_code == 200


# ── customer.subscription.updated ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_subscription_updated_syncs_status():
    from sqlalchemy import select

    import app.core.database as db_mod
    from app.models.plan import Plan
    from app.models.subscription import Subscription
    from app.models.user import User

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "wh4@test.com", "password": "StrongPass123!"},
        )

        # Seed plan + subscription
        async with db_mod.AsyncSessionLocal() as session:
            user_res = await session.execute(select(User).where(User.email == "wh4@test.com"))
            user = user_res.scalar_one()

            plan = Plan(
                name="pro",
                display_name="Pro",
                price_eur=2900,
                stripe_price_id="price_pro_wh",
                max_sites=5,
                scan_interval_days=7,
                tier_level=3,
                is_active=True,
            )
            session.add(plan)
            await session.flush()

            sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                stripe_customer_id="cus_wh4",
                stripe_subscription_id="sub_wh4_active",
                status="active",
                current_period_start=datetime(2024, 1, 1),
                current_period_end=datetime(2024, 2, 1),
            )
            session.add(sub)
            await session.commit()

        event = _make_event(
            "customer.subscription.updated",
            {
                "id": "sub_wh4_active",
                "status": "past_due",
                "current_period_end": 1705622400,
            },
        )

        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})

        assert r.status_code == 200

        async with db_mod.AsyncSessionLocal() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == "sub_wh4_active")
            )
            updated_sub = result.scalar_one_or_none()
        assert updated_sub is not None
        assert updated_sub.status == "past_due"


@pytest.mark.asyncio
async def test_subscription_deleted_syncs_status():
    from sqlalchemy import select

    import app.core.database as db_mod
    from app.models.plan import Plan
    from app.models.subscription import Subscription
    from app.models.user import User

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post(
            f"{BASE}/auth/register",
            json={"email": "wh5@test.com", "password": "StrongPass123!"},
        )

        async with db_mod.AsyncSessionLocal() as session:
            user_res = await session.execute(select(User).where(User.email == "wh5@test.com"))
            user = user_res.scalar_one()
            plan = Plan(
                name="starter2",
                display_name="Starter2",
                price_eur=990,
                stripe_price_id="price_s2",
                max_sites=1,
                scan_interval_days=30,
                tier_level=2,
                is_active=True,
            )
            session.add(plan)
            await session.flush()
            sub = Subscription(
                user_id=user.id,
                plan_id=plan.id,
                stripe_customer_id="cus_wh5",
                stripe_subscription_id="sub_wh5_cancel",
                status="active",
                current_period_start=datetime(2024, 1, 1),
                current_period_end=datetime(2024, 2, 1),
            )
            session.add(sub)
            await session.commit()

        event = _make_event(
            "customer.subscription.deleted",
            {
                "id": "sub_wh5_cancel",
                "status": "canceled",
            },
        )

        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})

        async with db_mod.AsyncSessionLocal() as session:
            result = await session.execute(
                select(Subscription).where(Subscription.stripe_subscription_id == "sub_wh5_cancel")
            )
            sub = result.scalar_one_or_none()
        assert sub.status == "canceled"


@pytest.mark.asyncio
async def test_subscription_updated_unknown_id_ignored():
    """stripe_subscription_id inconnu → pas de crash, réponse 200."""
    event = _make_event(
        "customer.subscription.updated",
        {
            "id": "sub_unknown_xyz",
            "status": "canceled",
        },
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_unknown_event_type_ignored():
    """Les types d'événements non gérés doivent être ignorés silencieusement."""
    event = _make_event("invoice.payment_failed", {"id": "inv_123"})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(WEBHOOK_URL, content=b"{}", headers={"stripe-signature": "mock"})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Branches d'erreur du webhook ──────────────────────────────────────────────
#
# Ces chemins etaient les 17 lignes non couvertes de webhooks.py, revelees le
# 2026-07-30 en remettant le fichier sous mesure de couverture. Ce sont
# exactement les branches qu'une montee majeure du SDK Stripe peut casser : elles
# lisent la FORME des payloads (items/data/price/id, metadata, customer_details).
# Les couvrir est le prerequis identifie avant de passer de stripe 10.x a 15.x.


@pytest.mark.asyncio
async def test_webhook_handler_failure_returns_500():
    """Un handler qui leve doit rendre 500 — Stripe reessaiera l'evenement.

    Le marqueur d'idempotence ne doit PAS etre pose : sinon la nouvelle tentative
    de Stripe serait ignoree et l'evenement perdu en silence.
    """
    event = _make_event("checkout.session.completed", {"customer": "cus_x"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with (
            patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event),
            patch(
                "app.api.v1.endpoints.webhooks._handle_checkout_completed",
                side_effect=RuntimeError("boom"),
            ),
        ):
            r = await c.post(
                WEBHOOK_URL,
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mock"},
            )
    assert r.status_code == 500

    # L'evenement ne doit pas avoir ete marque comme traite.
    from sqlalchemy import select

    import app.core.database as db_mod
    from app.models.processed_stripe_event import ProcessedStripeEvent

    async with db_mod.AsyncSessionLocal() as session:
        res = await session.execute(
            select(ProcessedStripeEvent).where(ProcessedStripeEvent.stripe_event_id == event["id"])
        )
        assert res.scalar_one_or_none() is None, (
            "l'evenement a ete marque traite malgre l'echec : Stripe ne reessaiera pas"
        )


@pytest.mark.asyncio
async def test_checkout_addon_extra_sites_increments_slots():
    """L'add-on `extra_sites` incremente les slots et sort sans toucher au plan."""
    import app.core.database as db_mod
    from app.core.config import settings
    from tests.conftest import register_and_login

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await register_and_login(c, "wh-addon@test.com")
        me = await c.get(f"{BASE}/users/me", headers=headers)
        user_id = me.json()["id"]

        # Abonnement actif requis : l'add-on s'y rattache.
        from app.models.plan import Plan
        from app.models.subscription import Subscription

        async with db_mod.AsyncSessionLocal() as session:
            plan = Plan(
                name="addon-plan",
                display_name="Addon",
                price_eur=4900,
                max_sites=1,
                scan_interval_days=30,
                tier_level=2,
                is_active=True,
            )
            session.add(plan)
            await session.flush()
            session.add(
                Subscription(user_id=user_id, plan_id=plan.id, status="active", extra_sites=0)
            )
            await session.commit()

        event = _make_event(
            "checkout.session.completed",
            {"metadata": {"addon_type": "extra_sites", "user_id": str(user_id)}},
        )
        with patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event):
            r = await c.post(
                WEBHOOK_URL,
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mock"},
            )
    assert r.status_code == 200

    from sqlalchemy import select

    async with db_mod.AsyncSessionLocal() as session:
        res = await session.execute(select(Subscription).where(Subscription.user_id == user_id))
        sub = res.scalar_one()
    assert sub.extra_sites == settings.ADDON_EXTRA_SITES_COUNT


@pytest.mark.asyncio
async def test_checkout_malformed_subscription_payload_is_ignored():
    """Payload d'abonnement sans price_id : on abandonne proprement, pas de 500.

    C'est LA branche sensible a une montee du SDK : elle depend de la forme
    exacte `items.data[0].price.id`.
    """
    event = _make_event(
        "checkout.session.completed",
        {
            "customer": "cus_bad",
            "subscription": "sub_bad",
            "customer_details": {"email": "wh-bad@test.com"},
        },
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        with (
            patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event),
            patch(
                "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
                return_value={"items": {"data": []}},  # forme inattendue
            ),
        ):
            r = await c.post(
                WEBHOOK_URL,
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mock"},
            )
    assert r.status_code == 200, "un payload inattendu ne doit pas faire echouer le webhook"


@pytest.mark.asyncio
async def test_checkout_unknown_user_does_not_create_subscription():
    """Email inconnu : aucun abonnement cree, et pas de 500."""
    from sqlalchemy import func, select

    import app.core.database as db_mod
    from app.models.plan import Plan
    from app.models.subscription import Subscription

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with db_mod.AsyncSessionLocal() as session:
            session.add(
                Plan(
                    name="ghost-plan",
                    display_name="Ghost",
                    price_eur=4900,
                    stripe_price_id="price_ghost",
                    max_sites=1,
                    scan_interval_days=30,
                    tier_level=2,
                    is_active=True,
                )
            )
            await session.commit()

        event = _make_event(
            "checkout.session.completed",
            {
                "customer": "cus_ghost",
                "subscription": "sub_ghost",
                "customer_details": {"email": "jamais-inscrit@test.com"},
            },
        )
        with (
            patch("app.api.v1.endpoints.webhooks.construct_webhook_event", return_value=event),
            patch(
                "app.api.v1.endpoints.webhooks.stripe.Subscription.retrieve",
                return_value={
                    "items": {"data": [{"price": {"id": "price_ghost"}}]},
                    "current_period_start": 1700000000,
                    "current_period_end": 1702678400,
                },
            ),
        ):
            r = await c.post(
                WEBHOOK_URL,
                content=json.dumps(event).encode(),
                headers={"stripe-signature": "mock"},
            )
    assert r.status_code == 200

    async with db_mod.AsyncSessionLocal() as session:
        n = await session.execute(select(func.count()).select_from(Subscription))
    assert n.scalar() == 0, "un email inconnu ne doit creer aucun abonnement"
