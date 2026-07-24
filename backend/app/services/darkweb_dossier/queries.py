"""Accès DB des dossiers Dark Web (CRUD + reset rescan + monitoring).

L'endpoint garde le façonnage HTTP (DossierOut / DossierListItem), le parsing
CSV, la génération PDF/CSV et le déclenchement du traitement en tâche de fond ;
ce module porte les requêtes et les frontières de transaction. Les fonctions
reçoivent des valeurs déjà préparées (nom nettoyé, domaine normalisé, liste
d'emails), jamais un schéma HTTP.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget


async def count_user_dossiers(db: AsyncSession, user_id: int) -> int:
    """Nombre de dossiers appartenant à l'utilisateur (quota par compte)."""
    result = await db.execute(select(DarkwebDossier).where(DarkwebDossier.user_id == user_id))
    return len(result.scalars().all())


async def create_dossier_with_targets(
    db: AsyncSession,
    *,
    user_id: int,
    company_name: str,
    domain: str,
    total_emails: int,
    emails: list[str],
) -> DarkwebDossier:
    """Crée le dossier (statut 'pending') et ses cibles email, en une transaction."""
    dossier = DarkwebDossier(
        user_id=user_id,
        company_name=company_name,
        domain=domain,
        status="pending",
        total_emails=total_emails,
    )
    db.add(dossier)
    await db.flush()

    for email in emails:
        db.add(DarkwebDossierTarget(dossier_id=dossier.id, email=email))

    await db.commit()
    await db.refresh(dossier)
    return dossier


async def list_user_dossiers(db: AsyncSession, user_id: int) -> list[DarkwebDossier]:
    """Dossiers de l'utilisateur, du plus récent au plus ancien."""
    result = await db.execute(
        select(DarkwebDossier)
        .where(DarkwebDossier.user_id == user_id)
        .order_by(DarkwebDossier.created_at.desc())
    )
    return list(result.scalars().all())


async def get_user_dossier(
    db: AsyncSession, dossier_id: int, user_id: int
) -> DarkwebDossier | None:
    """Dossier appartenant à l'utilisateur, sinon None."""
    result = await db.execute(
        select(DarkwebDossier).where(
            DarkwebDossier.id == dossier_id,
            DarkwebDossier.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def delete_dossier(db: AsyncSession, dossier: DarkwebDossier) -> None:
    """Supprime le dossier (cascade cibles via la relation)."""
    await db.delete(dossier)
    await db.commit()


async def reset_dossier_for_rescan(db: AsyncSession, dossier: DarkwebDossier) -> DarkwebDossier:
    """Réinitialise le dossier et ses cibles pour relancer le traitement."""
    await db.execute(
        DarkwebDossierTarget.__table__.update()
        .where(DarkwebDossierTarget.dossier_id == dossier.id)
        .values(
            status="pending",
            check_status="pending",
            total_breaches=0,
            breach_sources_json=None,
            checked_at=None,
        )
    )
    dossier.status = "pending"
    dossier.started_at = None
    dossier.finished_at = None
    dossier.risk_score = None
    dossier.severity_score = None
    dossier.error_message = None
    dossier.exposed_emails = 0
    dossier.total_breach_instances = 0
    dossier.top_sources_json = None
    dossier.checked_count = 0
    dossier.unverified_count = 0
    await db.commit()
    await db.refresh(dossier)
    return dossier


async def set_monitor(
    db: AsyncSession,
    dossier: DarkwebDossier,
    *,
    monitor_active: bool,
    next_monitor_at: datetime | None,
) -> DarkwebDossier:
    """Applique l'état de monitoring mensuel (valeurs calculées par l'endpoint)."""
    dossier.monitor_active = monitor_active
    dossier.next_monitor_at = next_monitor_at
    await db.commit()
    return dossier
