"""
Stripe service — subscription lifecycle management.
Requires STRIPE_SECRET_KEY in .env
"""

import stripe

from app.core.config import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

# Version d'API Stripe EPINGLEE explicitement.
#
# Sans cette ligne, la version d'API utilisee est celle par defaut du SDK — donc
# monter le SDK change AUSSI le contrat serveur (forme des payloads de webhook,
# champs des reponses) dans le meme commit. Deux risques melanges, impossibles a
# annuler separement.
#
# Avec l'epinglage, une montee du SDK devient un changement purement Python, et
# le passage a une version d'API plus recente devient une decision distincte,
# testable et reversible seule.
#
# Valeur = defaut du SDK 10.5.0, c'est-a-dire ce que la prod utilise deja :
# poser cette ligne ne change RIEN au comportement actuel.
STRIPE_API_VERSION = "2024-06-20"
stripe.api_version = STRIPE_API_VERSION


def create_customer(email: str) -> str:
    """Create a Stripe customer and return the customer ID."""
    customer = stripe.Customer.create(email=email)
    return customer.id


def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
    metadata: dict | None = None,
) -> str:
    """Create a Stripe Checkout Session and return the URL."""
    kwargs: dict = dict(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        automatic_tax={"enabled": True},
        billing_address_collection="auto",
        customer_update={"address": "auto"},
    )
    if metadata:
        kwargs["metadata"] = metadata
    session = stripe.checkout.Session.create(**kwargs)
    return session.url


def create_billing_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe Billing Portal session and return the URL."""
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def cancel_subscription(subscription_id: str) -> None:
    """Cancel a Stripe subscription immediately."""
    stripe.Subscription.cancel(subscription_id)


def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
    """Validate and parse a Stripe webhook event."""
    return stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
