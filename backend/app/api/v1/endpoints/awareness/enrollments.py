"""Endpoints inscriptions et dashboard learner (Sprint 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_learner
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_progress import AwarenessProgress
from app.schemas.awareness import (
    AwarenessEnrollmentOut,
    AwarenessModuleOut,
    AwarenessProgramOut,
    LearnerDashboard,
    LearnerModuleProgress,
)
from app.services import awareness_enrollment_service, awareness_program_service
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
    enrollments = await awareness_enrollment_service.list_learner_enrollments(db, learner.id)
    return [AwarenessEnrollmentOut.model_validate(e) for e in enrollments]


@router.get("/enrollments/{enrollment_id}/dashboard", response_model=LearnerDashboard)
async def learner_dashboard(
    enrollment_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> LearnerDashboard:
    """Retourne l'état complet d'une inscription : programme + progression par module."""
    enrollment = await awareness_enrollment_service.get_learner_enrollment(
        db, enrollment_id, learner.id
    )
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Inscription introuvable.")

    prog = await awareness_program_service.get_program_by_id(db, enrollment.program_id)
    if prog is None:
        raise HTTPException(status_code=404, detail="Programme introuvable.")
    mods = await awareness_program_service.list_active_modules(db, [prog.id])

    progress_map: dict[int, AwarenessProgress] = {}
    prog_records = await awareness_enrollment_service.list_progress_for_enrollment(
        db, enrollment_id
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
