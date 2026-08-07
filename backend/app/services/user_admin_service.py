"""Service admin des utilisateurs (lecture paginée + rôle consultant RSSI)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User
from app.services import subscription_service


async def list_users_with_plan(
    db: AsyncSession, *, skip: int, limit: int
) -> list[tuple[User, Subscription | None, Plan | None, bool]]:
    """Liste paginée des utilisateurs, leur abonnement, son plan, et sa VALIDITÉ.

    LA VALIDITÉ EST CALCULÉE PAR LA BASE, avec le prédicat que `get_active_plan`
    utilise lui-même. C'est ce qui garantit que le back-office et les accès
    disent la même chose : le 2026-08-07, cette liste appliquait sa propre règle
    — le statut seul — et affichait « Actif » avec un plan payant pendant que la
    plateforme traitait déjà le compte en Gratuit.

    LA JOINTURE RESTE SUR LE STATUT BRUT, DÉLIBÉRÉMENT. Filtrer directement sur
    la validité ferait disparaître l'abonnement périmé de la réponse, et
    l'administrateur verrait « Gratuit » sans jamais comprendre pourquoi. On
    remonte donc la ligne telle qu'elle est, plus le verdict sur sa validité :
    l'appelant peut ainsi montrer le plan effectif ET expliquer l'écart.
    """
    valide = subscription_service.abonnement_encore_valide()
    result = await db.execute(
        select(User, Subscription, Plan, valide.label("valide"))
        .outerjoin(
            Subscription,
            (Subscription.user_id == User.id) & (Subscription.status == "active"),
        )
        .outerjoin(Plan, Plan.id == Subscription.plan_id)
        .order_by(User.id.desc())
        .offset(skip)
        .limit(limit)
    )
    # Sans abonnement joint, le prédicat vaut NULL : on le lit comme « non valide ».
    return [(u, s, p, bool(v)) for u, s, p, v in result.all()]


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def toggle_rssi_consultant(db: AsyncSession, user: User) -> User:
    user.is_rssi_consultant = not user.is_rssi_consultant
    await db.commit()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()
