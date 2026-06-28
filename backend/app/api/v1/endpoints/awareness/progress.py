"""Endpoints progression / suivi des modules (Sprint 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_learner
from app.models.awareness_learner import AwarenessLearner
from app.schemas.awareness import (
    AwarenessEnrollmentOut,
    AwarenessProgressOut,
    CompleteModuleIn,
    HeartbeatIn,
)
from app.services.awareness_progression import (
    complete_module,
    heartbeat,
    start_module,
)

router = APIRouter()


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/start",
    response_model=AwarenessProgressOut,
)
async def start_module_endpoint(
    enrollment_id: int,
    module_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessProgressOut:
    progress = await start_module(db, learner, enrollment_id, module_id)
    return AwarenessProgressOut.model_validate(progress)


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/heartbeat",
    response_model=AwarenessProgressOut,
)
async def heartbeat_endpoint(
    enrollment_id: int,
    module_id: int,
    payload: HeartbeatIn,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessProgressOut:
    progress = await heartbeat(
        db, learner, enrollment_id, module_id, payload.elapsed_seconds, payload.video_position
    )
    return AwarenessProgressOut.model_validate(progress)


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/complete",
    response_model=AwarenessEnrollmentOut,
)
async def complete_module_endpoint(
    enrollment_id: int,
    module_id: int,
    payload: CompleteModuleIn,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessEnrollmentOut:
    enrollment = await complete_module(db, learner, enrollment_id, module_id, payload.quiz_score)
    return AwarenessEnrollmentOut.model_validate(enrollment)
