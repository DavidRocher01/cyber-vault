"""Service d'accès en LECTURE SEULE au portail client RSSI.

L'endpoint garde le façonnage HTTP (PortalMeOut / PortalActionOut / ...), le
calcul du score d'avancement, la construction des dicts pour le générateur PDF
et la signature d'URL S3 ; ce service porte uniquement les requêtes, toutes
scopées à un client (isolation via client_id fourni par la dépendance d'auth).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_action import RssiAction
from app.models.rssi_deliverable import RssiDeliverable
from app.models.rssi_visit import RssiVisit
from app.models.user import User


async def list_client_actions(db: AsyncSession, client_id: int) -> list[RssiAction]:
    """Actions du client, de la plus récente à la plus ancienne."""
    result = await db.execute(
        select(RssiAction)
        .where(RssiAction.client_id == client_id)
        .order_by(RssiAction.created_at.desc())
    )
    return list(result.scalars().all())


async def get_next_planned_visit(db: AsyncSession, client_id: int, today: date) -> RssiVisit | None:
    """Prochaine visite planifiée (à venir) du client, sinon None."""
    result = await db.execute(
        select(RssiVisit)
        .where(
            RssiVisit.client_id == client_id,
            RssiVisit.status == "planned",
            RssiVisit.scheduled_date >= today,
        )
        .order_by(RssiVisit.scheduled_date.asc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_user(db: AsyncSession, user_id: int) -> User | None:
    """Utilisateur (consultant) par identifiant, sinon None."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def list_client_visits(db: AsyncSession, client_id: int) -> list[RssiVisit]:
    """Visites du client, de la plus récente à la plus ancienne (date planifiée)."""
    result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client_id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    return list(result.scalars().all())


async def list_client_deliverables(db: AsyncSession, client_id: int) -> list[RssiDeliverable]:
    """Livrables du client, du plus récent au plus ancien (date de livraison)."""
    result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client_id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )
    return list(result.scalars().all())


async def get_client_deliverable(
    db: AsyncSession, deliverable_id: int, client_id: int
) -> RssiDeliverable | None:
    """Livrable appartenant à ce client, sinon None."""
    result = await db.execute(
        select(RssiDeliverable).where(
            RssiDeliverable.id == deliverable_id,
            RssiDeliverable.client_id == client_id,
        )
    )
    return result.scalar_one_or_none()
