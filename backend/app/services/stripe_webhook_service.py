"""Accès DB du handler de webhooks Stripe.

⚠️ Atomicité (à préserver) : le handler traite un événement puis marque
l'événement comme traité (ProcessedStripeEvent) en UN SEUL commit final. Toutes
les fonctions de ce service ne font que **poser** (stage) leurs changements sur
la session ; seule `mark_event_processed` committe — c'est le point de
persistance atomique. Ainsi, si le traitement échoue, rien n'est committé et
Stripe peut rejouer l'événement. Les lookups sont sans commit.

L'endpoint garde la vérification de signature (construct_webhook_event, patchée
en test), les appels à l'API Stripe (retrieve), le routage des types
d'événements et la conversion des timestamps ; ce service porte les requêtes et
le staging des mutations, à partir de valeurs déjà préparées.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.plan import Plan
from app.models.processed_stripe_event import ProcessedStripeEvent
from app.models.subscription import Subscription

# ── Idempotence ──────────────────────────────────────────────────────────────


async def is_event_processed(db: AsyncSession, event_id: str) -> bool:
    """True si l'événement Stripe a déjà été traité (idempotence)."""
    result = await db.execute(
        select(ProcessedStripeEvent).where(ProcessedStripeEvent.stripe_event_id == event_id)
    )
    return result.scalar_one_or_none() is not None


async def mark_event_processed(db: AsyncSession, event_id: str) -> None:
    """Marque l'événement comme traité et COMMITTE — point de persistance atomique.

    Ce commit persiste aussi tous les changements posés par les handlers durant
    le traitement de l'événement (même session/transaction).
    """
    db.add(ProcessedStripeEvent(stripe_event_id=event_id))
    await db.commit()


# ── Lookups (sans commit) ────────────────────────────────────────────────────


async def get_plan_by_price_id(db: AsyncSession, price_id: str) -> Plan | None:
    """Plan correspondant à un price_id Stripe, sinon None."""
    result = await db.execute(select(Plan).where(Plan.stripe_price_id == price_id))
    return result.scalar_one_or_none()


async def get_subscription_by_stripe_id(
    db: AsyncSession, subscription_id: str
) -> Subscription | None:
    """Abonnement local par identifiant d'abonnement Stripe, sinon None."""
    result = await db.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == subscription_id)
    )
    return result.scalar_one_or_none()


async def get_invoice_by_stripe_id(db: AsyncSession, stripe_invoice_id: str) -> Invoice | None:
    """Facture locale par identifiant de facture Stripe (anti-doublon), sinon None."""
    result = await db.execute(select(Invoice).where(Invoice.stripe_invoice_id == stripe_invoice_id))
    return result.scalar_one_or_none()


# ── Staging des mutations (PAS de commit — voir mark_event_processed) ─────────


def increment_extra_sites(sub: Subscription, count: int) -> None:
    """Ajoute des slots de sites supplémentaires (posé, non committé)."""
    sub.extra_sites += count


def upsert_checkout_subscription(
    db: AsyncSession,
    *,
    existing: Subscription | None,
    user_id: int,
    plan_id: int,
    customer_id: str,
    subscription_id: str,
    period_start: datetime,
    period_end: datetime,
) -> None:
    """Crée ou met à jour l'abonnement après un checkout réussi (posé, non committé)."""
    if existing:
        existing.plan_id = plan_id
        existing.stripe_customer_id = customer_id
        existing.stripe_subscription_id = subscription_id
        existing.status = "active"
        existing.current_period_start = period_start
        existing.current_period_end = period_end
    else:
        db.add(
            Subscription(
                user_id=user_id,
                plan_id=plan_id,
                stripe_customer_id=customer_id,
                stripe_subscription_id=subscription_id,
                status="active",
                current_period_start=period_start,
                current_period_end=period_end,
            )
        )


def apply_subscription_status(
    sub: Subscription, *, status: str, period_end: datetime | None
) -> None:
    """Applique un changement de statut/période d'abonnement (posé, non committé)."""
    sub.status = status
    if period_end is not None:
        sub.current_period_end = period_end
