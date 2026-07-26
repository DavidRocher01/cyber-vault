from datetime import datetime, timedelta

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

# Nom du plan Gratuit servant de repli côté lecture. Tout compte sans abonnement actif
# (inscription non finalisée, churn / abo annulé) retombe automatiquement sur ce palier :
# il garde l'accès Gratuit au lieu d'être verrouillé (max_sites=0). Le plan est semé au
# démarrage (main._seed_plans) ; en son absence (certains tests unitaires) le repli est
# inerte et les fonctions conservent leur comportement historique (None / 0).
FREE_PLAN_NAME = "free"


async def _get_free_plan(db: AsyncSession) -> Plan | None:
    """Retourne le plan Gratuit actif servant de repli, ou None s'il n'est pas semé."""
    result = await db.execute(
        select(Plan).where(Plan.name == FREE_PLAN_NAME, Plan.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def get_active_plan(db: AsyncSession, user_id: int) -> Plan | None:
    """Plan de l'abonnement actif de l'utilisateur.

    Repli sur le plan Gratuit si aucun abonnement actif (compte neuf ou churné) afin de
    ne jamais verrouiller un utilisateur ; None seulement si le Gratuit n'est pas semé.
    """
    result = await db.execute(
        select(Plan)
        .join(Subscription, Subscription.plan_id == Plan.id)
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    plan = result.scalar_one_or_none()
    if plan is None:
        plan = await _get_free_plan(db)
    return plan


async def get_active_tier(db: AsyncSession, user_id: int) -> int:
    """Return the tier level of the user's active subscription (DEFAULT_TIER if none)."""
    plan = await get_active_plan(db, user_id)
    return plan.tier_level if plan else DEFAULT_TIER


async def get_effective_max_sites(db: AsyncSession, user_id: int) -> int:
    """Return plan.max_sites + subscription.extra_sites for the active subscription.

    - Repli sur le plan Gratuit si aucun abonnement actif (compte neuf ou churné) : le
      quota du Gratuit s'applique au lieu de verrouiller l'ajout de sites (max_sites=0).
      0 seulement si le Gratuit n'est pas semé.
    - UNLIMITED_SITES (-1) si le plan autorise un nombre de sites illimité.
    """
    result = await db.execute(
        select(Subscription)
        .options(selectinload(Subscription.plan))
        .where(Subscription.user_id == user_id, Subscription.status == "active")
    )
    sub = result.scalar_one_or_none()
    if not sub:
        free = await _get_free_plan(db)
        if free is None:
            return 0
        return UNLIMITED_SITES if free.max_sites < 0 else free.max_sites
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


# Identifiant Stripe fictif posé sur les abonnements créés par override admin (piste A).
# Permet de distinguer un abonnement attribué manuellement (test de quotas, offre
# commerciale) d'un abonnement réel issu d'un checkout Stripe.
ADMIN_OVERRIDE_MARKER = "admin_override"


async def admin_set_user_plan(db: AsyncSession, *, user_id: int, plan: Plan, now: datetime) -> None:
    """Attribue (ou rétrograde) l'abonnement d'un utilisateur vers un plan SANS Stripe.

    Réservé à l'usage admin : tester les quotas / l'export / le scan d'un palier, ou
    offrir un plan à un client. La période est posée à ~10 ans (abonnement non facturé,
    aucun renouvellement à gérer). Sur un abonnement existant, seuls le plan, le statut et
    la période sont mis à jour ; les identifiants Stripe d'origine ne sont pas écrasés.
    """
    await upsert_active_subscription(
        db,
        user_id=user_id,
        plan_id=plan.id,
        now=now,
        period_end=now + timedelta(days=365 * 10),
        stripe_customer_id=ADMIN_OVERRIDE_MARKER,
        stripe_subscription_id=ADMIN_OVERRIDE_MARKER,
    )
