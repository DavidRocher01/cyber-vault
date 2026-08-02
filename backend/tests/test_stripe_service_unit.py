"""
Unit tests — app.services.stripe_service
Covers: create_customer, create_checkout_session, create_billing_portal_session,
        cancel_subscription, construct_webhook_event.
All Stripe API calls are mocked — no real network calls.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.pricing import COMPORTEMENT_TVA_ATTENDU

MODULE = "app.services.stripe_service"


def prix_stripe(montant=4900, intervalle="month", **surcharges):
    """Un objet Price plausible. `recurring` doit rester un vrai dict : le code
    appelle `.get('interval')` dessus, ce qu'un MagicMock accepterait sans rien
    verifier."""
    champs = {
        "active": True,
        "unit_amount": montant,
        "currency": "eur",
        "recurring": {"interval": intervalle},
        "tax_behavior": COMPORTEMENT_TVA_ATTENDU,
    }
    champs.update(surcharges)
    return MagicMock(**champs)


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
    def _call(
        self,
        customer_id="cus_x",
        price_id="price_x",
        success_url="https://app.com/success",
        cancel_url="https://app.com/cancel",
        montant_attendu=4900,
        intervalle_attendu="month",
    ):
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_test_abc"
        # La garde de facturation interroge Stripe avant d'ouvrir la session :
        # on lui repond un prix conforme pour rester sur le chemin nominal.
        with (
            patch(f"{MODULE}.stripe.Price.retrieve", return_value=prix_stripe(montant_attendu)),
            patch(
                f"{MODULE}.stripe.checkout.Session.create", return_value=mock_session
            ) as mock_create,
        ):
            from app.services.stripe_service import create_checkout_session

            url = create_checkout_session(
                customer_id,
                price_id,
                success_url,
                cancel_url,
                montant_attendu=montant_attendu,
                intervalle_attendu=intervalle_attendu,
            )
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
        with patch(
            f"{MODULE}.stripe.billing_portal.Session.create", return_value=mock_session
        ) as mock_create:
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
        with patch(
            f"{MODULE}.stripe.Webhook.construct_event", return_value=mock_event
        ) as mock_construct:
            from app.services.stripe_service import construct_webhook_event

            result = construct_webhook_event(b"payload", "sig_header")
        assert result is mock_event
        mock_construct.assert_called_once()

    def test_passes_payload_and_sig(self):
        mock_event = MagicMock()
        with patch(
            f"{MODULE}.stripe.Webhook.construct_event", return_value=mock_event
        ) as mock_construct:
            from app.services.stripe_service import construct_webhook_event

            construct_webhook_event(b"raw_body", "t=123,v1=abc")
        args = mock_construct.call_args[0]
        assert args[0] == b"raw_body"
        assert args[1] == "t=123,v1=abc"


# ── verifier_prix : la garde de facturation ──────────────────────────────────


class TestVerifierPrix:
    """Ce que ces tests protegent : un `stripe_price_id` n'est qu'une chaine en
    base. Rien n'empeche qu'il designe un tarif d'une generation precedente —
    sept prix perimes sont restes actifs chez Stripe jusqu'au 2026-08-02. Sans
    cette garde, un checkout aurait debite 9,90 EUR un abonnement affiche 49 EUR
    sans lever la moindre erreur."""

    def _verifier(self, prix, montant=4900, intervalle="month"):
        from app.services.stripe_service import verifier_prix

        with patch(f"{MODULE}.stripe.Price.retrieve", return_value=prix):
            verifier_prix("price_x", montant, intervalle)

    def test_prix_conforme_passe(self):
        self._verifier(prix_stripe(4900))

    def test_montant_different_refuse(self):
        from app.services.stripe_service import PrixStripeIncoherentError

        # Le cas reel : la base pointe encore le prix de juin a 14,90 EUR.
        with pytest.raises(PrixStripeIncoherentError, match="1490c au lieu de 4900c"):
            self._verifier(prix_stripe(1490))

    def test_prix_archive_refuse(self):
        from app.services.stripe_service import PrixStripeIncoherentError

        with pytest.raises(PrixStripeIncoherentError, match="archive"):
            self._verifier(prix_stripe(4900, active=False))

    def test_mauvaise_devise_refuse(self):
        from app.services.stripe_service import PrixStripeIncoherentError

        with pytest.raises(PrixStripeIncoherentError, match="devise"):
            self._verifier(prix_stripe(4900, currency="usd"))

    def test_mauvais_intervalle_refuse(self):
        """Facturer a l'annee un prix mensuel : douze fois trop peu percu."""
        from app.services.stripe_service import PrixStripeIncoherentError

        with pytest.raises(PrixStripeIncoherentError, match="intervalle"):
            self._verifier(prix_stripe(49000, intervalle="month"), 49000, "year")

    def test_tax_behavior_different_refuse(self):
        """Le jour ou la franchise en base de TVA tombera, `inclusive` mangerait
        20 % de marge en silence. La grille declare ce qu'elle attend."""
        from app.services.stripe_service import PrixStripeIncoherentError

        autre = "exclusive" if COMPORTEMENT_TVA_ATTENDU == "inclusive" else "inclusive"
        with pytest.raises(PrixStripeIncoherentError, match="tax_behavior"):
            self._verifier(prix_stripe(4900, tax_behavior=autre))

    def test_tous_les_ecarts_sont_rapportes(self):
        """Un message qui ne dirait que le premier probleme ferait perdre un
        aller-retour a chaque correction."""
        from app.services.stripe_service import PrixStripeIncoherentError

        with pytest.raises(PrixStripeIncoherentError) as err:
            self._verifier(prix_stripe(1490, currency="usd", active=False))
        message = str(err.value)
        assert "archive" in message
        assert "1490c" in message
        assert "usd" in message

    def test_aucune_session_creee_si_le_prix_diverge(self):
        """Le point essentiel : on refuse AVANT d'ouvrir le paiement."""
        from app.services.stripe_service import PrixStripeIncoherentError, create_checkout_session

        with (
            patch(f"{MODULE}.stripe.Price.retrieve", return_value=prix_stripe(1490)),
            patch(f"{MODULE}.stripe.checkout.Session.create") as session_create,
        ):
            with pytest.raises(PrixStripeIncoherentError):
                create_checkout_session(
                    "cus_x",
                    "price_x",
                    "https://app.com/ok",
                    "https://app.com/ko",
                    montant_attendu=4900,
                    intervalle_attendu="month",
                )
        session_create.assert_not_called()
