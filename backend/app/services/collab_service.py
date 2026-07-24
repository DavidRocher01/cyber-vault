"""Service d'acces aux collaborateurs de site (audit collaboratif).

L'endpoint garde la validation des roles, la generation du token et l'envoi
d'email ; ce service porte les requetes et les frontieres de transaction.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.collab import SiteCollaborator


async def list_for_site(db: AsyncSession, site_id: int) -> list[SiteCollaborator]:
    """Collaborateurs d'un site."""
    result = await db.execute(select(SiteCollaborator).where(SiteCollaborator.site_id == site_id))
    return list(result.scalars().all())


async def get_by_email_and_site(
    db: AsyncSession, site_id: int, email: str
) -> SiteCollaborator | None:
    """Collaborateur d'un site par email (pour detecter un doublon), sinon None."""
    result = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.site_id == site_id,
            SiteCollaborator.email == email,
        )
    )
    return result.scalar_one_or_none()


async def create_collaborator(
    db: AsyncSession,
    *,
    site_id: int,
    owner_user_id: int,
    email: str,
    role: str,
    invite_token: str,
) -> SiteCollaborator:
    """Cree une invitation de collaboration (statut pending)."""
    collab = SiteCollaborator(
        site_id=site_id,
        owner_user_id=owner_user_id,
        email=email,
        role=role,
        status="pending",
        invite_token=invite_token,
        invited_at=datetime.now(UTC),
    )
    db.add(collab)
    await db.commit()
    await db.refresh(collab)
    return collab


async def get_collaborator(
    db: AsyncSession, site_id: int, collab_id: int
) -> SiteCollaborator | None:
    """Collaborateur par id sur un site donne, sinon None."""
    result = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.id == collab_id,
            SiteCollaborator.site_id == site_id,
        )
    )
    return result.scalar_one_or_none()


async def update_role(db: AsyncSession, collab: SiteCollaborator, role: str) -> SiteCollaborator:
    """Met a jour le role d'un collaborateur."""
    collab.role = role
    await db.commit()
    await db.refresh(collab)
    return collab


async def delete_collaborator(db: AsyncSession, collab: SiteCollaborator) -> None:
    """Supprime un collaborateur."""
    await db.delete(collab)
    await db.commit()


async def get_by_token(db: AsyncSession, token: str) -> SiteCollaborator | None:
    """Invitation par son token, sinon None."""
    result = await db.execute(
        select(SiteCollaborator).where(SiteCollaborator.invite_token == token)
    )
    return result.scalar_one_or_none()


async def accept(db: AsyncSession, collab: SiteCollaborator) -> SiteCollaborator:
    """Marque une invitation comme acceptee."""
    collab.status = "accepted"
    collab.accepted_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(collab)
    return collab


async def list_accepted_for_email(db: AsyncSession, email: str) -> list[SiteCollaborator]:
    """Invitations acceptees pour un email donne."""
    result = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.email == email,
            SiteCollaborator.status == "accepted",
        )
    )
    return list(result.scalars().all())
