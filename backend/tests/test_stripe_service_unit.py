"""
Unit tests — app.services.stripe_service
Covers: create_customer, create_checkout_session, create_billing_portal_session,
        cancel_subscription, construct_webhook_event.
All Stripe API calls are mocked — no real network calls.
"""

import pytest
from unittest.mock import MagicMock, patch


MODULE = "app.services.stripe_service"


# ── create_customer ──────────────────────────────────────────────────────────

class TestCreateCustomer:
    def test_returns_customer_id(self):
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"
        with patch(f"{MODULE}.stripe.Customer.create", return_value=mock_customer) as mock_create:
            from app.services.stripe_service import create_customer
            result = create_customer("user@example.com")
        assert result == "cus_test123"
        mock_create.assert_called_once_with(email="user@example.com")

    def test_passes_email(self):
        mock_customer = MagicMock(id="cus_abc")
        with patch(f"{MODULE}.stripe.Customer.create", return_value=mock_customer) as mock_create:
            from app.services.stripe_service import create_customer
            create_customer("test@domain.com")
        _, kwargs = mock_create.call_args
        assert kwargs["email"] == "test@domain.com"


# ── create_checkout_session ──────────────────────────────────────────────────

class TestCreateCheckoutSession:
    def _call(self, customer_id="cus_x", price_id="price_x",
              success_url="https://app.com/success", cancel_url="https://app.com/cancel"):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
        with patch(f"{MODULE}.stripe.checkout.Session.create", return_value=mock_session) as mock_create:
            from app.services.stripe_service import create_checkout_session
            url = create_checkout_session(customer_id, price_id, success_url, cancel_url)
        return url, mock_create

    def test_returns_session_url(self):
        url, _ = self._call()
        assert url == "https://checkout.stripe.com/pay/cs_test_abc"

    def test_passes_correct_price(self):
        _, mock_create = self._call(price_id="price_starter")
        kwargs = mock_create.call_args[1]
        assert kwargs["line_items"][0]["price"] == "price_starter"

    def test_passes_correct_customer(self):
        _, mock_create = self._call(customer_id="cus_customer1")
        kwargs = mock_create.call_args[1]
        assert kwargs["customer"] == "cus_customer1"

    def test_mode_is_subscription(self):
        _, mock_create = self._call()
        kwargs = mock_create.call_args[1]
        assert kwargs["mode"] == "subscription"

    def test_automatic_tax_enabled(self):
        _, mock_create = self._call()
        kwargs = mock_create.call_args[1]
        assert kwargs.get("automatic_tax") == {"enabled": True}

    def test_billing_address_collection_set(self):
        _, mock_create = self._call()
        kwargs = mock_create.call_args[1]
        assert kwargs.get("billing_address_collection") == "auto"

    def test_customer_update_address_auto(self):
        _, mock_create = self._call()
        kwargs = mock_create.call_args[1]
        assert kwargs.get("customer_update") == {"address": "auto"}

    def test_success_and_cancel_urls_passed(self):
        _, mock_create = self._call(
            success_url="https://app.com/ok",
            cancel_url="https://app.com/cancel",
        )
        kwargs = mock_create.call_args[1]
        assert kwargs["success_url"] == "https://app.com/ok"
        assert kwargs["cancel_url"] == "https://app.com/cancel"


# ── create_billing_portal_session ────────────────────────────────────────────

class TestCreateBillingPortalSession:
    def test_returns_portal_url(self):
        mock_session = MagicMock()
        mock_session.url = "https://billing.stripe.com/session/abc"
        with patch(f"{MODULE}.stripe.billing_portal.Session.create", return_value=mock_session):
            from app.services.stripe_service import create_billing_portal_session
            url = create_billing_portal_session("cus_x", "https://app.com/dashboard")
        assert url == "https://billing.stripe.com/session/abc"

    def test_passes_customer_and_return_url(self):
        mock_session = MagicMock(url="https://billing.stripe.com/x")
        with patch(f"{MODULE}.stripe.billing_portal.Session.create", return_value=mock_session) as mock_create:
            from app.services.stripe_service import create_billing_portal_session
            create_billing_portal_session("cus_portal", "https://app.com/back")
        kwargs = mock_create.call_args[1]
        assert kwargs["customer"] == "cus_portal"
        assert kwargs["return_url"] == "https://app.com/back"


# ── cancel_subscription ──────────────────────────────────────────────────────

class TestCancelSubscription:
    def test_calls_stripe_cancel(self):
        with patch(f"{MODULE}.stripe.Subscription.cancel") as mock_cancel:
            from app.services.stripe_service import cancel_subscription
            cancel_subscription("sub_abc123")
        mock_cancel.assert_called_once_with("sub_abc123")


# ── construct_webhook_event ──────────────────────────────────────────────────

class TestConstructWebhookEvent:
    def test_returns_event_on_valid_payload(self):
        mock_event = MagicMock()
        with patch(f"{MODULE}.stripe.Webhook.construct_event", return_value=mock_event) as mock_construct:
            from app.services.stripe_service import construct_webhook_event
            result = construct_webhook_event(b"payload", "sig_header")
        assert result is mock_event
        mock_construct.assert_called_once()

    def test_passes_payload_and_sig(self):
        mock_event = MagicMock()
        with patch(f"{MODULE}.stripe.Webhook.construct_event", return_value=mock_event) as mock_construct:
            from app.services.stripe_service import construct_webhook_event
            construct_webhook_event(b"raw_body", "t=123,v1=abc")
        args = mock_construct.call_args[0]
        assert args[0] == b"raw_body"
        assert args[1] == "t=123,v1=abc"
