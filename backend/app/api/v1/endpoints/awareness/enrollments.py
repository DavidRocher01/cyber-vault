"""Endpoints inscriptions et dashboard learner (Sprint 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_learner
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress
from app.schemas.awareness import (
    AwarenessEnrollmentOut,
    AwarenessModuleOut,
    AwarenessProgramOut,
    LearnerDashboard,
    LearnerModuleProgress,
)
from app.services.awareness_progression import enroll_learner

router = APIRouter()


@router.post("/enrollments", response_model=AwarenessEnrollmentOut, status_code=201)
async def create_enrollment(
    program_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessEnrollmentOut:
    """Inscrit le learner authentifié à un programme."""
    enrollment = await enroll_learner(db, learner, program_id)
    return AwarenessEnrollmentOut.model_validate(enrollment)


@router.get("/enrollments", response_model=list[AwarenessEnrollmentOut])
async def list_enrollments(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessEnrollmentOut]:
    result = await db.execute(
        select(AwarenessEnrollment).where(AwarenessEnrollment.learner_id == learner.id)
    )
    return [AwarenessEnrollmentOut.model_validate(e) for e in result.scalars().all()]


@router.get("/enrollments/{enrollment_id}/dashboard", response_model=LearnerDashboard)
async def learner_dashboard(
    enrollment_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> LearnerDashboard:
    """Retourne l'état complet d'une inscription : programme + progression par module."""
    enrollment = (
        await db.execute(
            select(AwarenessEnrollment).where(
                AwarenessEnrollment.id == enrollment_id,
                AwarenessEnrollment.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Inscription introuvable.")

    prog = (
        await db.execute(
            select(AwarenessProgram).where(AwarenessProgram.id == enrollment.program_id)
        )
    ).scalar_one()
    mods = (
        (
            await db.execute(
                select(AwarenessModule)
                .where(AwarenessModule.program_id == prog.id, AwarenessModule.is_active == True)
                .order_by(AwarenessModule.position)
            )
        )
        .scalars()
        .all()
    )

    progress_map: dict[int, AwarenessProgress] = {}
    prog_records = (
        (
            await db.execute(
                select(AwarenessProgress).where(AwarenessProgress.enrollment_id == enrollment_id)
            )
        )
        .scalars()
        .all()
    )
    for p in prog_records:
        progress_map[p.module_id] = p

    modules_progress = []
    for mod in mods:
        p = progress_map.get(mod.id)
        modules_progress.append(
            LearnerModuleProgress(
                module_id=mod.id,
                slug=mod.slug,
                title=mod.title,
                position=mod.position,
                status=p.status if p else "not_started",
                time_spent_seconds=p.time_spent_seconds if p else 0,
                video_resume_position=p.video_resume_position if p else 0,
                best_quiz_score=p.best_quiz_score if p else None,
            )
        )

    prog_dict = {k: v for k, v in prog.__dict__.items() if not k.startswith("_")}
    prog_dict["modules"] = [AwarenessModuleOut.model_validate(m) for m in mods]
    prog_out = AwarenessProgramOut.model_validate(prog_dict)

    return LearnerDashboard(
        enrollment=AwarenessEnrollmentOut.model_validate(enrollment),
        program=prog_out,
        modules_progress=modules_progress,
    )
