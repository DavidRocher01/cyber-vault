"""
Progression service — gère l'avancement d'un learner dans un programme.

Opérations :
  enroll()         — inscrire un learner à un programme
  start_module()   — démarrer un module (crée un enregistrement progress)
  heartbeat()      — mettre à jour le temps passé + position vidéo
  complete_module()— marquer un module terminé + recalculer completion_pct
  _recompute_enrollment() — recalcule completion_pct et passe en "completed" si 100%
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress

# ── Enroll ────────────────────────────────────────────────────────────────────


async def enroll_learner(
    db: AsyncSession,
    learner: AwarenessLearner,
    program_id: int,
) -> AwarenessEnrollment:
    """
    Enroll a learner in a program.
    Returns existing enrollment if already enrolled.
    """
    program = (
        await db.execute(
            select(AwarenessProgram).where(
                AwarenessProgram.id == program_id,
                AwarenessProgram.is_active == True,
            )
        )
    ).scalar_one_or_none()
    if program is None:
        raise HTTPException(status_code=404, detail="Programme introuvable.")

    existing = (
        await db.execute(
            select(AwarenessEnrollment).where(
                AwarenessEnrollment.learner_id == learner.id,
                AwarenessEnrollment.program_id == program_id,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    enrollment = AwarenessEnrollment(
        learner_id=learner.id,
        program_id=program_id,
        organization_id=learner.organization_id,
        status="pending",
    )
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


# ── Start module ──────────────────────────────────────────────────────────────


async def start_module(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment_id: int,
    module_id: int,
) -> AwarenessProgress:
    """
    Mark a module as started for this enrollment.
    Returns existing progress record if already started.
    """
    enrollment = await _get_enrollment_or_403(db, learner, enrollment_id)
    await _get_module_in_program_or_404(db, module_id, enrollment.program_id)

    progress = (
        await db.execute(
            select(AwarenessProgress).where(
                AwarenessProgress.enrollment_id == enrollment_id,
                AwarenessProgress.module_id == module_id,
            )
        )
    ).scalar_one_or_none()

    if progress is None:
        progress = AwarenessProgress(
            enrollment_id=enrollment_id,
            module_id=module_id,
            status="in_progress",
            started_at=datetime.now(UTC),
        )
        db.add(progress)
    elif progress.status == "not_started":
        progress.status = "in_progress"
        progress.started_at = datetime.now(UTC)

    # Transition enrollment to in_progress
    if enrollment.status == "pending":
        enrollment.status = "in_progress"
        enrollment.started_at = datetime.now(UTC)
    enrollment.last_activity_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(progress)
    return progress


# ── Heartbeat ─────────────────────────────────────────────────────────────────


async def heartbeat(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment_id: int,
    module_id: int,
    elapsed_seconds: int,
    video_position: int | None = None,
) -> AwarenessProgress:
    """
    Update time_spent and optionally video_resume_position.
    elapsed_seconds: time since last heartbeat (typically 30s).
    """
    enrollment = await _get_enrollment_or_403(db, learner, enrollment_id)
    progress = (
        await db.execute(
            select(AwarenessProgress).where(
                AwarenessProgress.enrollment_id == enrollment_id,
                AwarenessProgress.module_id == module_id,
            )
        )
    ).scalar_one_or_none()

    if progress is None:
        raise HTTPException(
            status_code=404, detail="Progression introuvable — démarrez le module d'abord."
        )

    progress.time_spent_seconds += max(0, elapsed_seconds)
    progress.last_heartbeat_at = datetime.now(UTC)
    if video_position is not None:
        progress.video_resume_position = max(0, video_position)

    enrollment.last_activity_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(progress)
    return progress


# ── Complete module ───────────────────────────────────────────────────────────


async def complete_module(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment_id: int,
    module_id: int,
    quiz_score: int | None = None,
) -> AwarenessEnrollment:
    """
    Mark a module as completed (no quiz required, or quiz_score provided).
    Recalculates enrollment.completion_pct and may transition to "completed".
    Returns the updated enrollment.
    """
    enrollment = await _get_enrollment_or_403(db, learner, enrollment_id)
    module = await _get_module_in_program_or_404(db, module_id, enrollment.program_id)

    progress = (
        await db.execute(
            select(AwarenessProgress).where(
                AwarenessProgress.enrollment_id == enrollment_id,
                AwarenessProgress.module_id == module_id,
            )
        )
    ).scalar_one_or_none()

    if progress is None:
        progress = AwarenessProgress(
            enrollment_id=enrollment_id,
            module_id=module_id,
            started_at=datetime.now(UTC),
        )
        db.add(progress)

    # Validate quiz score if module requires it
    if module.has_quiz and quiz_score is not None:
        if quiz_score >= module.quiz_passing_score:
            progress.status = "completed"
        else:
            progress.status = "failed"
        progress.best_quiz_score = max(progress.best_quiz_score or 0, quiz_score)
    else:
        progress.status = "completed"

    progress.completed_at = datetime.now(UTC)
    enrollment.last_activity_at = datetime.now(UTC)

    await db.flush()
    await db.flush()
    await _recompute_enrollment(db, enrollment)
    await db.commit()
    await db.refresh(enrollment)

    # Auto-issue certificate when enrollment completes
    if enrollment.status == "completed":
        from app.services.awareness_certificate_service import issue_certificate
        await issue_certificate(db, enrollment)

    return enrollment


# ── Private helpers ───────────────────────────────────────────────────────────


async def _get_enrollment_or_403(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment_id: int,
) -> AwarenessEnrollment:
    enrollment = (
        await db.execute(
            select(AwarenessEnrollment).where(
                AwarenessEnrollment.id == enrollment_id,
                AwarenessEnrollment.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if enrollment is None:
        raise HTTPException(status_code=403, detail="Inscription introuvable.")
    return enrollment


async def _get_module_in_program_or_404(
    db: AsyncSession, module_id: int, program_id: int
) -> AwarenessModule:
    module = (
        await db.execute(
            select(AwarenessModule).where(
                AwarenessModule.id == module_id,
                AwarenessModule.program_id == program_id,
                AwarenessModule.is_active == True,
            )
        )
    ).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=404, detail="Module introuvable dans ce programme.")
    return module


async def _recompute_enrollment(db: AsyncSession, enrollment: AwarenessEnrollment) -> None:
    """Recalculate completion_pct; set status=completed when all modules are done."""
    total_modules = (
        await db.execute(
            select(func.count(AwarenessModule.id)).where(
                AwarenessModule.program_id == enrollment.program_id,
                AwarenessModule.is_active == True,
            )
        )
    ).scalar_one()

    if total_modules == 0:
        enrollment.completion_pct = 0.0
        return

    completed_modules = (
        await db.execute(
            select(func.count(AwarenessProgress.id)).where(
                AwarenessProgress.enrollment_id == enrollment.id,
                AwarenessProgress.status == "completed",
            )
        )
    ).scalar_one()

    enrollment.completion_pct = round(completed_modules / total_modules * 100, 1)

    if enrollment.completion_pct >= 100.0:
        enrollment.status = "completed"
        enrollment.completed_at = datetime.now(UTC)
