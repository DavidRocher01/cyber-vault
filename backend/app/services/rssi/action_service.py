"""Service d'accès aux actions RSSI (plan d'action d'un client consultant).

L'endpoint garde le façonnage HTTP (RssiActionOut), la validation du payload,
la logique de complétion (statut « done » -> completed_at) et la génération du
CSV ; ce service porte les requêtes et les frontières de transaction. Les
fonctions reçoivent des valeurs déjà préparées (dicts de champs modèle), jamais
un schéma HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_action import RssiAction
from app.models.rssi_visit import RssiVisit


async def list_actions(
    db: AsyncSession, client_id: int, status_filter: str | None = None
) -> list[RssiAction]:
    """Actions du client, filtrées par statut le cas échéant, plus récentes d'abord."""
    query = select(RssiAction).where(RssiAction.client_id == client_id)
    if status_filter:
        query = query.where(RssiAction.status == status_filter)
    query = query.order_by(RssiAction.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_visit_for_client(db: AsyncSession, visit_id: int, client_id: int) -> RssiVisit | None:
    """Visite appartenant à CE client (isolation source d'action), sinon None."""
    result = await db.execute(
        select(RssiVisit).where(
            RssiVisit.id == visit_id,
            RssiVisit.client_id == client_id,
        )
    )
    return result.scalar_one_or_none()


async def create_action(db: AsyncSession, *, client_id: int, values: dict) -> RssiAction:
    """Crée une action pour le client (dict de champs modèle déjà validés)."""
    action = RssiAction(client_id=client_id, **values)
    db.add(action)
    await db.commit()
    await db.refresh(action)
    return action


async def get_action(db: AsyncSession, action_id: int, client_id: int) -> RssiAction | None:
    """Action par identifiant appartenant à ce client, sinon None."""
    result = await db.execute(
        select(RssiAction).where(
            RssiAction.id == action_id,
            RssiAction.client_id == client_id,
        )
    )
    return result.scalar_one_or_none()


async def update_action(db: AsyncSession, action: RssiAction, values: dict) -> RssiAction:
    """Applique un patch partiel à l'action et met à jour updated_at."""
    for field, value in values.items():
        setattr(action, field, value)
    action.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(action)
    return action


async def delete_action(db: AsyncSession, action: RssiAction) -> None:
    """Supprime l'action."""
    await db.delete(action)
    await db.commit()
