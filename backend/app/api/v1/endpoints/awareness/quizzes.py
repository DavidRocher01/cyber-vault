"""Endpoints quiz et tentatives (Sprint 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.core.deps import get_current_learner
from app.models.awareness_learner import AwarenessLearner
from app.schemas.awareness import QuizResultOut, QuizStartOut, QuizSubmitIn
from app.services.awareness_quiz_engine import start_quiz, submit_quiz

router = APIRouter()


@router.get(
    "/enrollments/{enrollment_id}/modules/{module_id}/quiz",
    response_model=QuizStartOut,
)
async def get_quiz_questions(
    enrollment_id: int,
    module_id: int,
    request: Request,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> QuizStartOut:
    """
    Démarre une tentative de quiz — retourne les questions randomisées
    sans les réponses correctes.
    """
    ip = request.client.host if request.client else None
    result = await start_quiz(db, learner, enrollment_id, module_id, ip)
    return QuizStartOut(**result)


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/quiz/submit",
    response_model=QuizResultOut,
)
async def submit_quiz_answers(
    enrollment_id: int,
    module_id: int,
    payload: QuizSubmitIn,
    request: Request,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> QuizResultOut:
    """
    Soumet les réponses, calcule le score, persiste la tentative.
    Si réussi, complète automatiquement le module.
    """
    ip = request.client.host if request.client else None
    result = await submit_quiz(
        db,
        learner,
        enrollment_id,
        module_id,
        payload.answers,
        payload.duration_seconds,
        ip,
    )
    return QuizResultOut(**result)
