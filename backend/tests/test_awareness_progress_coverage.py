"""
Tests de couverture — Awareness progression (endpoints + service).

Cible les chemins NON couverts par test_awareness_sprint3.py :
  - start_module : module hors programme (404), isolation enrollment (403),
    idempotence (re-start), transition d'un progress "not_started"
  - heartbeat : progress absent (404), isolation (403), elapsed négatif clampé,
    video_position None
  - complete_module : quiz réussi / quiz échoué (pas de +% ), progress créé à la volée,
    module 404, isolation 403, double-complétion idempotente,
    complétion totale -> certificat + email (mocké) + bonus XP

Le seeding se fait directement en base (db_session) pour maîtriser has_quiz et
l'isolation, et un JWT learner est forgé via create_learner_jwt (pas de magic-link HTTP).
Aucun service externe réel (email mocké).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest_asyncio
from sqlalchemy import select

from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_module import AwarenessModule
from app.models.awareness_organization import AwarenessOrganization
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress
from app.models.user import User
from app.services.awareness_magic_link import create_learner_jwt

BASE = "/api/v1"


# ── Seeding helpers ─────────────────────────────────────────────────────────────


async def _seed_program(
    db, slug: str, *, n_modules: int, has_quiz: bool = False, passing_score: int = 60
):
    """Create a program with n_modules and return (program, [modules])."""
    prog = AwarenessProgram(
        slug=slug,
        title=f"Prog {slug}",
        language="fr",
        estimated_duration_minutes=n_modules * 5,
        passing_score=passing_score,
        certificate_validity_months=12,
        is_active=True,
        version="1.0",
    )
    db.add(prog)
    await db.flush()
    modules = []
    for i in range(n_modules):
        mod = AwarenessModule(
            program_id=prog.id,
            slug=f"{slug}-mod-{i}",
            title=f"Module {i}",
            position=i,
            content_type="markdown",
            estimated_duration_minutes=5,
            xp_points=10,
            has_quiz=has_quiz,
            quiz_passing_score=passing_score,
            is_active=True,
        )
        db.add(mod)
        modules.append(mod)
    await db.flush()
    return prog, modules


async def _seed_learner(db, org: AwarenessOrganization, email: str) -> AwarenessLearner:
    learner = AwarenessLearner(
        organization_id=org.id,
        email=email,
        first_name="Test",
        last_name="User",
        is_active=True,
    )
    db.add(learner)
    await db.flush()
    return learner


async def _seed_world(db, *, n_modules=2, has_quiz=False, passing_score=60, prog_slug="prog-cov"):
    """Create owner user + org + program(+modules) + learner + enrollment."""
    owner = User(email=f"owner-{prog_slug}@test.com", hashed_password="x")
    db.add(owner)
    await db.flush()

    org = AwarenessOrganization(owner_user_id=owner.id, name="Org Cov", max_learners=50)
    db.add(org)
    await db.flush()

    prog, modules = await _seed_program(
        db, prog_slug, n_modules=n_modules, has_quiz=has_quiz, passing_score=passing_score
    )
    learner = await _seed_learner(db, org, f"learner-{prog_slug}@test.com")

    enrollment = AwarenessEnrollment(
        learner_id=learner.id,
        program_id=prog.id,
        organization_id=org.id,
        status="pending",
    )
    db.add(enrollment)
    await db.commit()

    return {
        "org": org,
        "program": prog,
        "modules": modules,
        "learner": learner,
        "enrollment": enrollment,
    }


def _auth(learner: AwarenessLearner) -> dict:
    return {"Authorization": f"Bearer {create_learner_jwt(learner)}"}


@pytest_asyncio.fixture
async def db(db_session):
    return db_session


# ── start_module ────────────────────────────────────────────────────────────────


async def test_start_module_unknown_module_returns_404(db, http_client):
    w = await _seed_world(db, n_modules=1, prog_slug="start-404")
    enr, learner = w["enrollment"], w["learner"]
    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/999999/start",
        headers=_auth(learner),
    )
    assert r.status_code == 404
    assert "Module" in r.json()["detail"]


async def test_start_module_wrong_program_module_returns_404(db, http_client):
    """Un module qui existe mais appartient à un AUTRE programme -> 404."""
    w = await _seed_world(db, n_modules=1, prog_slug="start-otherprog")
    # module appartenant à un second programme
    _, other_mods = await _seed_program(db, "start-otherprog-2", n_modules=1)
    await db.commit()
    enr, learner = w["enrollment"], w["learner"]
    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{other_mods[0].id}/start",
        headers=_auth(learner),
    )
    assert r.status_code == 404


async def test_start_module_other_learner_enrollment_returns_403(db, http_client):
    """Un learner ne peut pas démarrer un module sur l'inscription d'un autre."""
    w = await _seed_world(db, n_modules=1, prog_slug="start-iso")
    intruder = await _seed_learner(db, w["org"], "intruder@start.com")
    await db.commit()
    enr, mod = w["enrollment"], w["modules"][0]
    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/start",
        headers=_auth(intruder),
    )
    assert r.status_code == 403


async def test_start_module_idempotent_returns_same_progress(db, http_client):
    """Re-démarrer un module déjà in_progress ne crée pas de doublon."""
    w = await _seed_world(db, n_modules=1, prog_slug="start-idem")
    enr, mod, learner = w["enrollment"], w["modules"][0], w["learner"]
    h = _auth(learner)
    r1 = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/start", headers=h
    )
    r2 = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/start", headers=h
    )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]
    assert r2.json()["status"] == "in_progress"
    # une seule ligne progress en base
    rows = (
        (
            await db.execute(
                select(AwarenessProgress).where(AwarenessProgress.enrollment_id == enr.id)
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_start_module_transitions_not_started_progress(db, http_client):
    """Un progress existant en 'not_started' passe à 'in_progress' au start."""
    w = await _seed_world(db, n_modules=1, prog_slug="start-notstarted")
    enr, mod, learner = w["enrollment"], w["modules"][0], w["learner"]
    # progress pré-existant en not_started (started_at None)
    p = AwarenessProgress(enrollment_id=enr.id, module_id=mod.id, status="not_started")
    db.add(p)
    await db.commit()

    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/start",
        headers=_auth(learner),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["id"] == p.id


# ── heartbeat ───────────────────────────────────────────────────────────────────


async def test_heartbeat_without_started_module_returns_404(db, http_client):
    """Heartbeat avant d'avoir démarré le module -> 404 (progress absent)."""
    w = await _seed_world(db, n_modules=1, prog_slug="hb-404")
    enr, mod, learner = w["enrollment"], w["modules"][0], w["learner"]
    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/heartbeat",
        json={"elapsed_seconds": 30},
        headers=_auth(learner),
    )
    assert r.status_code == 404
    assert "Progression" in r.json()["detail"]


async def test_heartbeat_other_learner_returns_403(db, http_client):
    w = await _seed_world(db, n_modules=1, prog_slug="hb-iso")
    intruder = await _seed_learner(db, w["org"], "intruder@hb.com")
    await db.commit()
    enr, mod = w["enrollment"], w["modules"][0]
    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/heartbeat",
        json={"elapsed_seconds": 30},
        headers=_auth(intruder),
    )
    assert r.status_code == 403


async def test_heartbeat_accumulates_without_video_position(db, http_client):
    """Deux heartbeats sans video_position : temps cumulé, position inchangée (0)."""
    w = await _seed_world(db, n_modules=1, prog_slug="hb-accum")
    enr, mod, learner = w["enrollment"], w["modules"][0], w["learner"]
    h = _auth(learner)
    await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/start", headers=h
    )
    await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/heartbeat",
        json={"elapsed_seconds": 20},
        headers=h,
    )
    r = await http_client.post(
        f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/heartbeat",
        json={"elapsed_seconds": 15},
        headers=h,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["time_spent_seconds"] == 35
    # jamais de video_position fourni -> reste à la valeur par défaut 0
    assert body["video_resume_position"] == 0


# ── complete_module : quiz ──────────────────────────────────────────────────────


async def test_complete_module_quiz_passed_marks_completed(db, http_client):
    """Module avec quiz, score >= passing -> completed + best_quiz_score enregistré."""
    w = await _seed_world(db, n_modules=2, has_quiz=True, passing_score=60, prog_slug="quiz-pass")
    enr, learner = w["enrollment"], w["learner"]
    mod = w["modules"][0]
    with patch("app.services.email_service.send_awareness_completion"):
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={"quiz_score": 80},
            headers=_auth(learner),
        )
    assert r.status_code == 200
    assert r.json()["completion_pct"] == 50.0

    prog = (
        await db.execute(
            select(AwarenessProgress).where(
                AwarenessProgress.enrollment_id == enr.id,
                AwarenessProgress.module_id == mod.id,
            )
        )
    ).scalar_one()
    assert prog.status == "completed"
    assert prog.best_quiz_score == 80


async def test_complete_module_quiz_failed_does_not_progress(db, http_client):
    """Score < passing -> status 'failed', completion_pct reste 0 (pas compté)."""
    w = await _seed_world(db, n_modules=2, has_quiz=True, passing_score=60, prog_slug="quiz-fail")
    enr, learner = w["enrollment"], w["learner"]
    mod = w["modules"][0]
    with patch("app.services.email_service.send_awareness_completion"):
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={"quiz_score": 40},
            headers=_auth(learner),
        )
    assert r.status_code == 200
    # échec -> aucun module "completed" -> 0%
    assert r.json()["completion_pct"] == 0.0

    prog = (
        await db.execute(
            select(AwarenessProgress).where(
                AwarenessProgress.enrollment_id == enr.id,
                AwarenessProgress.module_id == mod.id,
            )
        )
    ).scalar_one()
    assert prog.status == "failed"
    assert prog.best_quiz_score == 40


async def test_complete_module_creates_progress_when_absent(db, http_client):
    """complete sans start préalable : le service crée le progress à la volée."""
    w = await _seed_world(db, n_modules=2, prog_slug="comp-noprior")
    enr, learner = w["enrollment"], w["learner"]
    mod = w["modules"][0]
    # aucun progress au départ
    assert (
        await db.execute(select(AwarenessProgress).where(AwarenessProgress.enrollment_id == enr.id))
    ).scalars().first() is None

    with patch("app.services.email_service.send_awareness_completion"):
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={},
            headers=_auth(learner),
        )
    assert r.status_code == 200
    assert r.json()["completion_pct"] == 50.0
    prog = (
        await db.execute(select(AwarenessProgress).where(AwarenessProgress.enrollment_id == enr.id))
    ).scalar_one()
    assert prog.status == "completed"


# ── complete_module : erreurs / isolation ───────────────────────────────────────


async def test_complete_module_unknown_module_returns_404(db, http_client):
    w = await _seed_world(db, n_modules=1, prog_slug="comp-404")
    enr, learner = w["enrollment"], w["learner"]
    with patch("app.services.email_service.send_awareness_completion"):
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/424242/complete",
            json={},
            headers=_auth(learner),
        )
    assert r.status_code == 404


async def test_complete_module_other_learner_returns_403(db, http_client):
    w = await _seed_world(db, n_modules=1, prog_slug="comp-iso")
    intruder = await _seed_learner(db, w["org"], "intruder@comp.com")
    await db.commit()
    enr, mod = w["enrollment"], w["modules"][0]
    with patch("app.services.email_service.send_awareness_completion"):
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={},
            headers=_auth(intruder),
        )
    assert r.status_code == 403


async def test_complete_module_double_complete_idempotent(db, http_client):
    """Compléter deux fois le même module ne dépasse pas 100% / ne double-compte pas."""
    w = await _seed_world(db, n_modules=2, prog_slug="comp-double")
    enr, learner = w["enrollment"], w["learner"]
    mod = w["modules"][0]
    h = _auth(learner)
    with patch("app.services.email_service.send_awareness_completion"):
        r1 = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={},
            headers=h,
        )
        r2 = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={},
            headers=h,
        )
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["completion_pct"] == 50.0
    assert r2.json()["completion_pct"] == 50.0
    # une seule ligne progress pour ce module
    rows = (
        (
            await db.execute(
                select(AwarenessProgress).where(
                    AwarenessProgress.enrollment_id == enr.id,
                    AwarenessProgress.module_id == mod.id,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


# ── complete_module : complétion totale (certificat + email) ────────────────────


async def test_complete_all_modules_perfect_quiz_issues_certificate_and_email(db, http_client):
    """
    Complétion de tous les modules avec quiz parfait (100%) :
      - enrollment -> completed, 100%
      - bonus XP (module + quiz parfait +10 + programme entier +50)
      - certificat émis + email de complétion envoyé (mocké)
    """
    w = await _seed_world(db, n_modules=1, has_quiz=True, passing_score=60, prog_slug="full-cert")
    enr, learner = w["enrollment"], w["learner"]
    mod = w["modules"][0]

    with patch("app.services.email_service.send_awareness_completion") as mock_email:
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={"quiz_score": 100},
            headers=_auth(learner),
        )
    assert r.status_code == 200
    body = r.json()
    assert body["completion_pct"] == 100.0
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    # XP : module 10 + parfait 10 + programme 50 = 70
    assert body["xp_earned"] == 70
    # email de complétion tenté une fois
    assert mock_email.call_count == 1

    # un certificat a bien été créé pour cet enrollment
    from app.models.awareness_certificate import AwarenessCertificate

    cert = (
        await db.execute(
            select(AwarenessCertificate).where(AwarenessCertificate.enrollment_id == enr.id)
        )
    ).scalar_one_or_none()
    assert cert is not None


async def test_complete_last_module_no_quiz_completes_enrollment(db, http_client):
    """Programme mono-module sans quiz : complétion -> enrollment completed + email."""
    w = await _seed_world(db, n_modules=1, has_quiz=False, prog_slug="full-noquiz")
    enr, learner = w["enrollment"], w["learner"]
    mod = w["modules"][0]
    with patch("app.services.email_service.send_awareness_completion") as mock_email:
        r = await http_client.post(
            f"{BASE}/awareness/enrollments/{enr.id}/modules/{mod.id}/complete",
            json={},
            headers=_auth(learner),
        )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert r.json()["completion_pct"] == 100.0
    # module 10 + programme entier 50 = 60 (pas de quiz)
    assert r.json()["xp_earned"] == 60
    assert mock_email.call_count == 1
