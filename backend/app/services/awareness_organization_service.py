"""Service CRUD des organisations awareness + inscription en masse (bulk enroll)."""

from __future__ import annotations

from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.utils import mask_email
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.services.awareness_magic_link import issue_magic_link
from app.services.email_service import send_awareness_magic_link


async def create_organization(
    db: AsyncSession,
    *,
    owner_user_id: int,
    name: str,
    siret: str | None,
    sector: str | None,
    max_learners: int,
) -> AwarenessOrganization:
    """Cree une organisation awareness pour le proprietaire donne."""
    org = AwarenessOrganization(
        owner_user_id=owner_user_id,
        name=name,
        siret=siret,
        sector=sector,
        max_learners=max_learners,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


async def list_organizations_with_counts(
    db: AsyncSession, owner_user_id: int
) -> list[tuple[AwarenessOrganization, int]]:
    """Organisations d'un proprietaire avec le nombre de learners actifs."""
    rows = (
        await db.execute(
            select(
                AwarenessOrganization,
                func.count(AwarenessLearner.id).label("learner_count"),
            )
            .outerjoin(
                AwarenessLearner,
                (AwarenessLearner.organization_id == AwarenessOrganization.id)
                & (AwarenessLearner.is_active == True),  # noqa: E712
            )
            .where(AwarenessOrganization.owner_user_id == owner_user_id)
            .group_by(AwarenessOrganization.id)
        )
    ).all()
    return [(org, learner_count) for org, learner_count in rows]


async def get_organization_with_count(
    db: AsyncSession, org_id: int, owner_user_id: int
) -> tuple[AwarenessOrganization, int] | None:
    """Organisation (avec compte de learners actifs) si elle appartient au proprietaire, sinon None."""
    row = (
        await db.execute(
            select(
                AwarenessOrganization,
                func.count(AwarenessLearner.id).label("learner_count"),
            )
            .outerjoin(
                AwarenessLearner,
                (AwarenessLearner.organization_id == AwarenessOrganization.id)
                & (AwarenessLearner.is_active == True),  # noqa: E712
            )
            .where(
                AwarenessOrganization.id == org_id,
                AwarenessOrganization.owner_user_id == owner_user_id,
            )
            .group_by(AwarenessOrganization.id)
        )
    ).one_or_none()
    if row is None:
        return None
    org, learner_count = row
    return org, learner_count


async def save_organization(db: AsyncSession, org: AwarenessOrganization) -> AwarenessOrganization:
    """Persiste les modifications d'une organisation."""
    await db.commit()
    await db.refresh(org)
    return org


async def enroll_all_learners(
    db: AsyncSession, org: AwarenessOrganization, program_id: int
) -> dict:
    """Inscrit tous les learners actifs de l'organisation a un programme.

    Ignore les learners deja inscrits. Envoie un email magic-link a chaque nouvel inscrit.
    """
    learners_result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.organization_id == org.id,
            AwarenessLearner.is_active == True,  # noqa: E712
        )
    )
    learners = learners_result.scalars().all()

    # Precharge en UNE requete les inscriptions deja existantes pour ce programme
    # parmi ces learners (evite un N+1 : sinon une requete SELECT par learner).
    learner_ids = [learner.id for learner in learners]
    already_enrolled: set[int] = set()
    if learner_ids:
        existing_rows = await db.execute(
            select(AwarenessEnrollment.learner_id).where(
                AwarenessEnrollment.program_id == program_id,
                AwarenessEnrollment.learner_id.in_(learner_ids),
            )
        )
        already_enrolled = set(existing_rows.scalars().all())

    enrolled = 0
    skipped = 0
    for learner in learners:
        if learner.id in already_enrolled:
            skipped += 1
            continue
        enrollment = AwarenessEnrollment(
            learner_id=learner.id,
            program_id=program_id,
            organization_id=org.id,
            status="pending",
        )
        db.add(enrollment)
        enrolled += 1

        # Send magic-link invitation
        try:
            magic_result = await issue_magic_link(db, str(learner.email), org.id)
            if magic_result:
                _, raw_token = magic_result
                login_url = f"{settings.FRONTEND_URL}/awareness/login?token={raw_token}"
                send_awareness_magic_link(
                    to_email=str(learner.email),
                    first_name=learner.first_name,
                    org_name=org.name,
                    login_url=login_url,
                )
        except Exception as e:
            logger.warning(f"Envoi email magic-link echoue pour {mask_email(learner.email)}: {e}")

    await db.commit()
    return {"enrolled": enrolled, "skipped": skipped, "total": len(learners)}
