"""
Quiz engine — parse, randomise, score, and validate quiz attempts.

YAML quiz format (stored in AwarenessModule.quiz_yaml):

    questions:
      - id: q1
        type: single_choice | multiple_choice | true_false
        weight: 1          # points value (default 1)
        text: "Question ?"
        answers:
          - id: a
            text: "Réponse A"
            correct: true
          - id: b
            text: "Réponse B"
            correct: false
        explanation: "Explication affichée après soumission"

Engine behaviour:
  - Pool size: all questions in the YAML
  - Questions served per attempt: min(pool_size, QUESTIONS_PER_ATTEMPT)
  - Question order: randomised per attempt
  - Answer order: randomised per attempt
  - Correct answers: NEVER sent to the client on start
  - Score: weighted sum of correct / max possible weighted sum × 100
  - Cooldown: quiz_cooldown_minutes between failed attempts
  - Max attempts: quiz_max_attempts (0 = unlimited)
"""
from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta

import yaml
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_module import AwarenessModule
from app.models.awareness_quiz_attempt import AwarenessQuizAttempt

QUESTIONS_PER_ATTEMPT = 5  # number of questions drawn from the pool per attempt


# ── YAML parsing ──────────────────────────────────────────────────────────────

def parse_quiz_yaml(raw: str) -> list[dict]:
    """Parse quiz YAML and return the full question pool."""
    data = yaml.safe_load(raw)
    if not isinstance(data, dict) or "questions" not in data:
        raise ValueError("Format YAML quiz invalide : clé 'questions' manquante.")
    questions = data["questions"]
    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("Le quiz ne contient aucune question.")
    return questions


def _sanitize_for_client(question: dict) -> dict:
    """Return question dict without correct/explanation fields (anti-cheat)."""
    return {
        "id": question["id"],
        "type": question.get("type", "single_choice"),
        "weight": question.get("weight", 1),
        "text": question["text"],
        "answers": [
            {"id": a["id"], "text": a["text"]}
            for a in question.get("answers", [])
        ],
    }


def draw_questions(pool: list[dict], seed: int | None = None) -> list[dict]:
    """
    Draw QUESTIONS_PER_ATTEMPT questions from the pool at random.
    Randomise both question order and answer order.
    Returns client-safe dicts (no correct/explanation).
    """
    rng = random.Random(seed)
    selected = rng.sample(pool, min(len(pool), QUESTIONS_PER_ATTEMPT))
    result = []
    for q in selected:
        q_copy = dict(q)
        answers = list(q_copy.get("answers", []))
        rng.shuffle(answers)
        q_copy["answers"] = answers
        result.append(_sanitize_for_client(q_copy))
    return result


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_attempt(pool: list[dict], submitted: dict[str, list[str]]) -> tuple[int, list[dict]]:
    """
    Score submitted answers against the pool.

    submitted: {question_id: [chosen_answer_ids]}

    Returns (score_0_100, answer_details_list)
    where answer_details = [{question_id, chosen, correct_ids, is_correct, points_earned}]
    """
    pool_by_id = {q["id"]: q for q in pool}
    total_weight = 0
    earned_weight = 0
    details = []

    for q_id, chosen in submitted.items():
        q = pool_by_id.get(q_id)
        if q is None:
            continue
        weight = q.get("weight", 1)
        total_weight += weight
        correct_ids = {a["id"] for a in q.get("answers", []) if a.get("correct")}
        chosen_set = set(chosen) if isinstance(chosen, list) else {chosen}
        is_correct = chosen_set == correct_ids
        points = weight if is_correct else 0
        earned_weight += points
        details.append({
            "question_id": q_id,
            "chosen_answers": list(chosen_set),
            "correct_answers": list(correct_ids),
            "is_correct": is_correct,
            "points_earned": points,
            "explanation": q.get("explanation"),
        })

    if total_weight == 0:
        return 0, details
    score = round(earned_weight / total_weight * 100)
    return score, details


# ── Attempt lifecycle ─────────────────────────────────────────────────────────

async def start_quiz(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment_id: int,
    module_id: int,
    ip_address: str | None = None,
) -> dict:
    """
    Validate attempt eligibility and return randomised questions (no correct answers).
    Returns {"questions": [...], "attempt_number": N}
    """
    module = await _get_module_or_403(db, module_id, enrollment_id, learner)

    if not module.has_quiz or not module.quiz_yaml:
        raise HTTPException(status_code=422, detail="Ce module n'a pas de quiz.")

    pool = _parse_or_400(module.quiz_yaml)

    # Count previous attempts
    attempt_count = (
        await db.execute(
            select(func.count(AwarenessQuizAttempt.id)).where(
                AwarenessQuizAttempt.learner_id == learner.id,
                AwarenessQuizAttempt.module_id == module_id,
            )
        )
    ).scalar_one()

    if module.quiz_max_attempts > 0 and attempt_count >= module.quiz_max_attempts:
        raise HTTPException(
            status_code=422,
            detail=f"Nombre maximum de tentatives atteint ({module.quiz_max_attempts}).",
        )

    # Check cooldown on last failed attempt
    last_failed = (
        await db.execute(
            select(AwarenessQuizAttempt)
            .where(
                AwarenessQuizAttempt.learner_id == learner.id,
                AwarenessQuizAttempt.module_id == module_id,
                AwarenessQuizAttempt.result == "failed",
            )
            .order_by(AwarenessQuizAttempt.started_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if last_failed and module.quiz_cooldown_minutes > 0:
        cooldown_end = last_failed.started_at + timedelta(minutes=module.quiz_cooldown_minutes)
        if datetime.now(UTC) < cooldown_end:
            remaining = int((cooldown_end - datetime.now(UTC)).total_seconds() // 60) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Cooldown actif — réessayez dans {remaining} minute(s).",
            )

    questions = draw_questions(pool)
    return {
        "questions": questions,
        "attempt_number": attempt_count + 1,
        "module_id": module_id,
        "enrollment_id": enrollment_id,
    }


async def submit_quiz(
    db: AsyncSession,
    learner: AwarenessLearner,
    enrollment_id: int,
    module_id: int,
    answers: dict[str, list[str]],
    duration_seconds: int,
    ip_address: str | None = None,
) -> dict:
    """
    Score the submitted answers, persist the attempt, and update module progress.
    Returns full result including correct answers and explanations.
    """
    module = await _get_module_or_403(db, module_id, enrollment_id, learner)
    pool = _parse_or_400(module.quiz_yaml or "")

    score, details = score_attempt(pool, answers)
    result = "passed" if score >= module.quiz_passing_score else "failed"

    # Attempt count for number
    attempt_count = (
        await db.execute(
            select(func.count(AwarenessQuizAttempt.id)).where(
                AwarenessQuizAttempt.learner_id == learner.id,
                AwarenessQuizAttempt.module_id == module_id,
            )
        )
    ).scalar_one()

    attempt = AwarenessQuizAttempt(
        learner_id=learner.id,
        module_id=module_id,
        attempt_number=attempt_count + 1,
        score=score,
        result=result,
        duration_seconds=max(0, duration_seconds),
        answers_json=json.dumps(details),
        ip_address=ip_address,
        started_at=datetime.now(UTC) - timedelta(seconds=max(0, duration_seconds)),
        completed_at=datetime.now(UTC),
    )
    db.add(attempt)
    await db.flush()

    # Auto-complete module if passed
    if result == "passed":
        from app.services.awareness_progression import complete_module
        enrollment = await complete_module(db, learner, enrollment_id, module_id, score)
    else:
        await db.commit()
        enrollment = None

    return {
        "score": score,
        "result": result,
        "passing_score": module.quiz_passing_score,
        "attempt_number": attempt.attempt_number,
        "details": details,
        "enrollment_completion_pct": enrollment.completion_pct if enrollment else None,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_module_or_403(
    db: AsyncSession,
    module_id: int,
    enrollment_id: int,
    learner: AwarenessLearner,
) -> AwarenessModule:
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

    module = (
        await db.execute(
            select(AwarenessModule).where(
                AwarenessModule.id == module_id,
                AwarenessModule.program_id == enrollment.program_id,
                AwarenessModule.is_active == True,
            )
        )
    ).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=404, detail="Module introuvable.")
    return module


def _parse_or_400(raw: str) -> list[dict]:
    try:
        return parse_quiz_yaml(raw)
    except (ValueError, yaml.YAMLError) as exc:
        raise HTTPException(status_code=422, detail=f"Quiz YAML invalide : {exc}") from exc
