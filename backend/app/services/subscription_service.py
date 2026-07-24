from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.plan import Plan
from app.models.subscription import Subscription

# Sentinelle "sites illimités" : un plan dont max_sites est < 0 (ex. Gratuit) n'impose
# aucune limite de nombre de sites. Repris tel quel par get_effective_max_sites afin que
# les appelants (sites.py, scans.py) puissent shortcut la vérification de quota.
UNLIMITED_SITES = -1

# Tier de repli quand l'utilisateur n'a pas d'abonnement actif : 1 (Gratuit). Sûr pour la
# profondeur de scan (tiers 1 et 2 exécutent les mêmes modules de base) et correct pour le
# gating (un compte sans abonnement ne doit pas accéder aux features tier >= 2).
DEFAULT_TIER = 1


async def get_active_plan(db: AsyncSession, user_id: int) -> Plan | None:
    """Return the user's active subscription plan, or None if no active subscription."""
    result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    return result.scalar_one_or_none()


async def get_active_tier(db: AsyncSession, user_id: int) -> int:
    """Return the tier level of the user's active subscription (DEFAULT_TIER if none)."""
    plan = await get_active_plan(db, user_id)
    return plan.tier_level if plan else DEFAULT_TIER


async def get_effective_max_sites(db: AsyncSession, user_id: int) -> int:
    """Return plan.max_sites + subscription.extra_sites for the active subscription.

    - 0 si aucun abonnement actif (onboarding non terminé -> "abonnement requis").
    - UNLIMITED_SITES (-1) si le plan autorise un nombre de sites illimité (ex. Gratuit).
    """
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    sub = result.scalar_one_or_none()
    if not sub:
        return 0
    if sub.plan.max_sites < 0:
        return UNLIMITED_SITES
    return sub.plan.max_sites + sub.extra_sites


async def get_active_subscription_with_plan(db: AsyncSession, user_id: int) -> Subscription | None:
    """Abonnement actif de l'utilisateur avec son plan chargé, sinon None."""
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    return result.scalar_one_or_none()


async def get_active_subscription(db: AsyncSession, user_id: int) -> Subscription | None:
    """Abonnement actif de l'utilisateur, sinon None."""
    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    return result.scalar_one_or_none()


async def get_subscription(db: AsyncSession, user_id: int) -> Subscription | None:
    """Abonnement de l'utilisateur quel que soit son statut, sinon None."""
    result = await db.execute(select(Subscription).where(Subscription.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_active_subscription(
    db: AsyncSession,
    *,
    user_id: int,
    plan_id: int,
    now: datetime,
    period_end: datetime,
    stripe_customer_id: str | None,
    stripe_subscription_id: str | None,
) -> None:
    """Active ou met à jour l'abonnement de l'utilisateur (checkout dev/gratuit).

    Sur un abonnement existant, seuls le plan, le statut et la période sont
    mis à jour ; les identifiants Stripe ne sont posés qu'à la création.
    """
    existing = await get_subscription(db, user_id)
    if existing:
        existing.plan_id = plan_id
        existing.status = "active"
        existing.current_period_start = now
        existing.current_period_end = period_end
    else:
        db.add(
            Subscription(
                user_id=user_id,
                plan_id=plan_id,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                status="active",
                current_period_start=now,
                current_period_end=period_end,
            )
        )
    await db.commit()


async def add_extra_sites(db: AsyncSession, sub: Subscription, count: int) -> None:
    """Incrémente le nombre de sites supplémentaires d'un abonnement."""
    sub.extra_sites += count
    await db.commit()
