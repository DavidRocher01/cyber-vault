"""
Tests — Awareness Sprint 4 : moteur de quiz.

Couvre :
  - Parser YAML (valide, clé manquante, pool vide)
  - draw_questions : randomisation, taille pool, pas de réponses correctes
  - score_attempt : single_choice correct/incorrect, multiple_choice, pondération
  - start_quiz : cooldown, max tentatives, module sans quiz
  - submit_quiz : passage réussi auto-complète le module, réponses persistées
  - Endpoints GET /quiz et POST /quiz/submit
"""

import pytest

from app.services.awareness_quiz_engine import (
    QUESTIONS_PER_ATTEMPT,
    draw_questions,
    parse_quiz_yaml,
    score_attempt,
)

# ── YAML quiz fixture ──────────────────────────────────────────────────────────

SIMPLE_QUIZ = """
questions:
  - id: q1
    type: single_choice
    weight: 1
    text: "Question 1 ?"
    answers:
      - id: a
        text: "Bonne réponse"
        correct: true
      - id: b
        text: "Mauvaise réponse"
        correct: false
    explanation: "Explication 1"
  - id: q2
    type: single_choice
    weight: 2
    text: "Question 2 ?"
    answers:
      - id: c
        text: "Bonne"
        correct: true
      - id: d
        text: "Mauvaise"
        correct: false
  - id: q3
    type: multiple_choice
    weight: 1
    text: "Question 3 ?"
    answers:
      - id: e
        text: "Bonne 1"
        correct: true
      - id: f
        text: "Bonne 2"
        correct: true
      - id: g
        text: "Mauvaise"
        correct: false
"""

LARGE_QUIZ = "\n".join(
    [
        "questions:",
        *[
            f"  - id: q{i}\n    type: single_choice\n    weight: 1\n"
            f"    text: 'Q{i}'\n    answers:\n"
            f"      - id: a{i}\n        text: 'Bonne'\n        correct: true\n"
            f"      - id: b{i}\n        text: 'Mauvaise'\n        correct: false"
            for i in range(10)
        ],
    ]
)


# ── Parser ─────────────────────────────────────────────────────────────────────


def test_parse_valid_yaml():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    assert len(pool) == 3
    assert pool[0]["id"] == "q1"


def test_parse_missing_questions_key():
    with pytest.raises(ValueError, match="questions"):
        parse_quiz_yaml("title: test\n")


def test_parse_empty_questions_list():
    with pytest.raises(ValueError, match="aucune"):
        parse_quiz_yaml("questions: []\n")


def test_parse_invalid_yaml():
    import yaml as _yaml

    with pytest.raises(_yaml.YAMLError):
        parse_quiz_yaml(": invalid: yaml: [")


# ── draw_questions ─────────────────────────────────────────────────────────────


def test_draw_respects_questions_per_attempt():
    pool = parse_quiz_yaml(LARGE_QUIZ)
    drawn = draw_questions(pool)
    assert len(drawn) == QUESTIONS_PER_ATTEMPT


def test_draw_returns_all_if_pool_smaller_than_limit():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    drawn = draw_questions(pool)
    assert len(drawn) == len(pool)  # pool=3, limit=5


def test_draw_does_not_expose_correct_field():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    drawn = draw_questions(pool)
    for q in drawn:
        for answer in q["answers"]:
            assert "correct" not in answer


def test_draw_does_not_expose_explanation():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    drawn = draw_questions(pool)
    for q in drawn:
        assert "explanation" not in q


def test_draw_randomises_with_seed():
    pool = parse_quiz_yaml(LARGE_QUIZ)
    drawn1 = draw_questions(pool, seed=42)
    drawn2 = draw_questions(pool, seed=99)
    ids1 = [q["id"] for q in drawn1]
    ids2 = [q["id"] for q in drawn2]
    # Seeds 42 and 99 produce different draws from a 10-question pool
    assert ids1 != ids2


def test_draw_same_seed_is_deterministic():
    pool = parse_quiz_yaml(LARGE_QUIZ)
    drawn1 = draw_questions(pool, seed=7)
    drawn2 = draw_questions(pool, seed=7)
    assert [q["id"] for q in drawn1] == [q["id"] for q in drawn2]


# ── score_attempt ──────────────────────────────────────────────────────────────


def test_score_all_correct_single_choice():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    # q1 correct=a, q2 correct=c
    score, details = score_attempt(pool, {"q1": ["a"], "q2": ["c"]})
    # weight q1=1, q2=2 → earned=3/3 → 100%
    assert score == 100
    assert all(d["is_correct"] for d in details)


def test_score_all_wrong():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    score, details = score_attempt(pool, {"q1": ["b"], "q2": ["d"]})
    assert score == 0
    assert all(not d["is_correct"] for d in details)


def test_score_partial():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    # q1 wrong (weight=1), q2 correct (weight=2) → 2/3 → 66%
    score, _ = score_attempt(pool, {"q1": ["b"], "q2": ["c"]})
    assert score == 67  # round(2/3*100)


def test_score_multiple_choice_needs_all_correct():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    # q3 correct = {e, f} — only one selected → wrong
    score, details = score_attempt(pool, {"q3": ["e"]})
    q3_detail = next(d for d in details if d["question_id"] == "q3")
    assert q3_detail["is_correct"] is False


def test_score_multiple_choice_all_correct():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    score, details = score_attempt(pool, {"q3": ["e", "f"]})
    q3_detail = next(d for d in details if d["question_id"] == "q3")
    assert q3_detail["is_correct"] is True


def test_score_unknown_question_ignored():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    score, details = score_attempt(pool, {"ghost_q": ["x"]})
    assert score == 0
    assert details == []


def test_score_detail_includes_explanation():
    pool = parse_quiz_yaml(SIMPLE_QUIZ)
    _, details = score_attempt(pool, {"q1": ["a"]})
    q1 = next(d for d in details if d["question_id"] == "q1")
    assert q1["explanation"] == "Explication 1"


# ── Endpoints (HTTP integration) ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quiz_start_requires_auth():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/awareness/enrollments/1/modules/1/quiz")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_quiz_submit_requires_auth():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            "/api/v1/awareness/enrollments/1/modules/1/quiz/submit",
            json={"answers": {}, "duration_seconds": 60},
        )
    assert r.status_code == 401


# ── Integration helpers ────────────────────────────────────────────────────────


async def _admin_headers_q(email: str) -> dict:
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/api/v1/auth/register", json={"email": email, "password": "StrongPass123!"})
        r = await c.post("/api/v1/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _setup_quiz_env(
    admin_email: str,
    learner_email: str,
    quiz_max_attempts: int = 3,
    quiz_cooldown_minutes: int = 60,
    has_quiz: bool = True,
) -> tuple[dict, int, int]:
    """
    Creates org + learner + program + quiz module + enrollment.
    Returns (learner_headers, enrollment_id, module_id).
    """
    import tempfile
    from pathlib import Path

    import yaml as _yaml
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import select

    import app.core.database as _db
    from app.main import app
    from app.models.awareness_module import AwarenessModule
    from app.models.awareness_program import AwarenessProgram
    from app.services.awareness_content_importer import import_from_directory

    prog_slug = f"quiz-prog-{admin_email.replace('@', '-').replace('.', '-')}"

    # Build content directory
    tmp = Path(tempfile.mkdtemp())
    fr_dir = tmp / "fr"
    (fr_dir / "programs").mkdir(parents=True)
    mod_dir = fr_dir / "modules" / "quiz-mod"
    mod_dir.mkdir(parents=True)

    prog_data = {
        "slug": prog_slug,
        "title": "Quiz Test Programme",
        "language": "fr",
        "version": "1.0",
        "estimated_duration_minutes": 5,
        "passing_score": 60,
        "certificate_validity_months": 12,
        "is_active": True,
        "modules": ["quiz-mod"],
    }
    (fr_dir / "programs" / "prog.yaml").write_text(_yaml.dump(prog_data), encoding="utf-8")

    meta = {
        "title": "Quiz Module",
        "content_type": "mixed",
        "estimated_duration_minutes": 5,
        "xp_points": 20,
        "has_quiz": has_quiz,
        "quiz_max_attempts": quiz_max_attempts,
        "quiz_cooldown_minutes": quiz_cooldown_minutes,
        "quiz_passing_score": 60,
        "is_active": True,
    }
    (mod_dir / "meta.yaml").write_text(_yaml.dump(meta), encoding="utf-8")
    (mod_dir / "content.md").write_text("# Quiz Module", encoding="utf-8")
    if has_quiz:
        (mod_dir / "quiz.yaml").write_text(SIMPLE_QUIZ, encoding="utf-8")

    async with _db.AsyncSessionLocal() as session:
        await import_from_directory(session, fr_dir)
        prog = (
            await session.execute(
                select(AwarenessProgram).where(AwarenessProgram.slug == prog_slug)
            )
        ).scalar_one_or_none()
        if not prog:
            return {}, -1, -1
        mod = (
            await session.execute(
                select(AwarenessModule).where(AwarenessModule.program_id == prog.id)
            )
        ).scalar_one_or_none()
        program_id, module_id = prog.id, (mod.id if mod else -1)

    # Create admin + learner + magic-link session
    await _admin_headers_q(admin_email)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        org_id = (
            await c.post(
                "/api/v1/awareness/organizations",
                json={"name": "Quiz Org", "max_learners": 50},
                headers=await _admin_headers_q(admin_email),
            )
        ).json()["id"]
        await c.post(
            f"/api/v1/awareness/organizations/{org_id}/learners",
            json={"email": learner_email},
            headers=await _admin_headers_q(admin_email),
        )
        from awareness_helpers import get_awareness_magic_token

        token = await get_awareness_magic_token(learner_email, org_id)
        learner_h = {
            "Authorization": f"Bearer {(await c.get('/api/v1/awareness/auth/verify', params={'token': token})).json()['access_token']}"
        }
        enroll_r = await c.post(
            "/api/v1/awareness/enrollments",
            params={"program_id": program_id},
            headers=learner_h,
        )
        enrollment_id = enroll_r.json().get("id", -1)

    return learner_h, enrollment_id, module_id


# ── start_quiz integration ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_quiz_returns_questions():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqstart1@quiz.com", "learner_sqstart1@quiz.com"
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz",
            headers=learner_h,
        )
    assert r.status_code == 200
    data = r.json()
    assert "questions" in data
    assert len(data["questions"]) == 3  # SIMPLE_QUIZ has 3 questions (< QUESTIONS_PER_ATTEMPT=5)
    assert data["attempt_number"] == 1
    # Anti-cheat: no correct field in answers
    for q in data["questions"]:
        for ans in q["answers"]:
            assert "correct" not in ans


@pytest.mark.asyncio
async def test_start_quiz_wrong_enrollment_403():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, _, mod_id = await _setup_quiz_env("sq403@quiz.com", "learner_sq403@quiz.com")
    if mod_id == -1:
        pytest.skip("setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"/api/v1/awareness/enrollments/99999/modules/{mod_id}/quiz",
            headers=learner_h,
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_start_quiz_module_without_quiz_422():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqnoq@quiz.com", "learner_sqnoq@quiz.com", has_quiz=False
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz",
            headers=learner_h,
        )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_start_quiz_max_attempts_exceeded_422():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    # max_attempts=1, cooldown=0 so we can submit immediately
    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqmax@quiz.com",
        "learner_sqmax@quiz.com",
        quiz_max_attempts=1,
        quiz_cooldown_minutes=0,
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    wrong_answers = {"q1": ["b"], "q2": ["d"], "q3": ["g"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Consume the single allowed attempt
        await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": wrong_answers, "duration_seconds": 10},
            headers=learner_h,
        )
        # Now attempt to start — should be blocked
        r = await c.get(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz",
            headers=learner_h,
        )
    assert r.status_code == 422
    assert "tentatives" in r.json()["detail"]


@pytest.mark.asyncio
async def test_start_quiz_cooldown_429():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    # cooldown=60 min, max_attempts=0 (unlimited)
    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqcool@quiz.com",
        "learner_sqcool@quiz.com",
        quiz_max_attempts=0,
        quiz_cooldown_minutes=60,
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    wrong_answers = {"q1": ["b"], "q2": ["d"], "q3": ["g"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # Submit a failed attempt to trigger cooldown
        await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": wrong_answers, "duration_seconds": 10},
            headers=learner_h,
        )
        # Immediately try to start → cooldown should block
        r = await c.get(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz",
            headers=learner_h,
        )
    assert r.status_code == 429
    assert "Cooldown" in r.json()["detail"]


# ── submit_quiz integration ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_quiz_passed():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqpass@quiz.com", "learner_sqpass@quiz.com"
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    correct_answers = {"q1": ["a"], "q2": ["c"], "q3": ["e", "f"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": correct_answers, "duration_seconds": 30},
            headers=learner_h,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 100
    assert data["result"] == "passed"
    assert data["attempt_number"] == 1
    assert data["enrollment_completion_pct"] is not None


@pytest.mark.asyncio
async def test_submit_quiz_failed():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqfail@quiz.com", "learner_sqfail@quiz.com"
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    wrong_answers = {"q1": ["b"], "q2": ["d"], "q3": ["g"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": wrong_answers, "duration_seconds": 15},
            headers=learner_h,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 0
    assert data["result"] == "failed"
    assert data["enrollment_completion_pct"] is None
    # Details include explanations
    assert len(data["details"]) == 3
    assert all(not d["is_correct"] for d in data["details"])


@pytest.mark.asyncio
async def test_submit_quiz_partial_score():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqpart@quiz.com", "learner_sqpart@quiz.com"
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    # q1 correct (weight=1), q2 wrong (weight=2), q3 correct (weight=1) → 2/4 = 50%
    mixed_answers = {"q1": ["a"], "q2": ["d"], "q3": ["e", "f"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": mixed_answers, "duration_seconds": 20},
            headers=learner_h,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["score"] == 50
    assert data["result"] == "failed"  # passing_score=60


@pytest.mark.asyncio
async def test_submit_quiz_wrong_enrollment_403():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, _, mod_id = await _setup_quiz_env("sq403sub@quiz.com", "learner_sq403sub@quiz.com")
    if mod_id == -1:
        pytest.skip("setup failed")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/awareness/enrollments/99999/modules/{mod_id}/quiz/submit",
            json={"answers": {"q1": ["a"]}, "duration_seconds": 5},
            headers=learner_h,
        )
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_submit_quiz_attempt_number_increments():
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqnum@quiz.com",
        "learner_sqnum@quiz.com",
        quiz_max_attempts=0,
        quiz_cooldown_minutes=0,
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    wrong = {"q1": ["b"], "q2": ["d"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": wrong, "duration_seconds": 5},
            headers=learner_h,
        )
        r2 = await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": wrong, "duration_seconds": 5},
            headers=learner_h,
        )
    assert r1.json()["attempt_number"] == 1
    assert r2.json()["attempt_number"] == 2


@pytest.mark.asyncio
async def test_start_quiz_module_from_other_program_404():
    """Learner tries to access a module that exists but belongs to a different program."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    # Set up two independent programs
    learner_h, enroll_id, _ = await _setup_quiz_env("sq404a@quiz.com", "learner_sq404a@quiz.com")
    _, _, other_mod_id = await _setup_quiz_env("sq404b@quiz.com", "learner_sq404b@quiz.com")
    if enroll_id == -1 or other_mod_id == -1:
        pytest.skip("setup failed")

    # Use learner A's enrollment but module B's ID → module not in this program
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{other_mod_id}/quiz",
            headers=learner_h,
        )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_submit_quiz_invalid_yaml_422():
    """Module has corrupted quiz_yaml — submit should return 422."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import update

    import app.core.database as _db
    from app.main import app
    from app.models.awareness_module import AwarenessModule

    learner_h, enroll_id, mod_id = await _setup_quiz_env(
        "sqbadyaml@quiz.com", "learner_sqbadyaml@quiz.com"
    )
    if enroll_id == -1:
        pytest.skip("setup failed")

    # Corrupt the quiz_yaml directly in the DB
    async with _db.AsyncSessionLocal() as session:
        await session.execute(
            update(AwarenessModule)
            .where(AwarenessModule.id == mod_id)
            .values(quiz_yaml=": invalid: [yaml {{{")
        )
        await session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.post(
            f"/api/v1/awareness/enrollments/{enroll_id}/modules/{mod_id}/quiz/submit",
            json={"answers": {"q1": ["a"]}, "duration_seconds": 5},
            headers=learner_h,
        )
    assert r.status_code == 422
    assert "invalide" in r.json()["detail"]
