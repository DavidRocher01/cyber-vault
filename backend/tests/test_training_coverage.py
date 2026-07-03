"""
Couverture des chemins NON couverts de app/api/v1/endpoints/training.py.

Cible : la branche "awareness" de _load_all_modules + la conversion
_awareness_module_to_training (et ses cas limites : pas de quiz, questions vides,
< 2 réponses, pas de bonne réponse, YAML corrompu, slug inconnu → méta par défaut),
ainsi que le flux HTTP get_modules / complete / progress sur un module awareness.

Ces chemins ne sont pas exercés par test_training_unit.py, qui mocke la DB et
court-circuite systématiquement la branche awareness (AwarenessProgram → None).

asyncio_mode=auto : les tests sont des `async def test_...` sans décorateur.
"""

import textwrap

from sqlalchemy import select

from app.api.v1.endpoints.training import _awareness_module_to_training
from app.models.awareness_module import AwarenessModule
from app.models.awareness_program import AwarenessProgram
from app.models.training_progress import TrainingProgress
from app.models.user import User

BASE = "/api/v1"


# ── Helpers de seeding ──────────────────────────────────────────────────────────


def _quiz_yaml(*, question: str = "Question awareness ?", with_correct: bool = True) -> str:
    correct_b = "true" if with_correct else "false"
    return textwrap.dedent(
        f"""\
        questions:
          - id: q1
            type: single_choice
            text: "{question}"
            answers:
              - id: a
                text: "Mauvaise"
                correct: false
              - id: b
                text: "Bonne"
                correct: {correct_b}
            explanation: "Explication awareness."
        """
    )


async def _seed_program(db, *, slug: str = "nis2-essentiel") -> AwarenessProgram:
    prog = AwarenessProgram(
        slug=slug,
        title="Programme NIS2",
        language="fr",
        is_active=True,
        version="1.0",
    )
    db.add(prog)
    await db.flush()
    return prog


async def _seed_module(
    db,
    program: AwarenessProgram,
    *,
    slug: str,
    position: int = 0,
    quiz_yaml: str | None = None,
    is_active: bool = True,
    title: str = "Module awareness",
    description: str | None = "Description awareness.",
    duration: int = 7,
) -> AwarenessModule:
    mod = AwarenessModule(
        program_id=program.id,
        slug=slug,
        title=title,
        description=description,
        position=position,
        content_type="markdown",
        estimated_duration_minutes=duration,
        has_quiz=True,
        quiz_yaml=quiz_yaml,
        is_active=is_active,
    )
    db.add(mod)
    await db.flush()
    return mod


# ── _awareness_module_to_training : cas limites (unitaire, sans DB) ──────────────


def test_convert_returns_none_when_no_quiz_yaml():
    mod = AwarenessModule(slug="ransomware", title="X", quiz_yaml=None)
    assert _awareness_module_to_training(mod) is None


def test_convert_returns_none_when_no_questions():
    mod = AwarenessModule(slug="ransomware", title="X", quiz_yaml="questions: []\n")
    assert _awareness_module_to_training(mod) is None


def test_convert_returns_none_when_fewer_than_two_answers():
    yaml_one_answer = textwrap.dedent(
        """\
        questions:
          - id: q1
            text: "Seule réponse ?"
            answers:
              - id: a
                text: "Unique"
                correct: true
        """
    )
    mod = AwarenessModule(slug="ransomware", title="X", quiz_yaml=yaml_one_answer)
    assert _awareness_module_to_training(mod) is None


def test_convert_falls_back_to_first_answer_when_no_correct_flag():
    mod = AwarenessModule(
        slug="ransomware",
        title="X",
        quiz_yaml=_quiz_yaml(with_correct=False),
        estimated_duration_minutes=5,
        description="d",
    )
    out = _awareness_module_to_training(mod)
    assert out is not None
    # Aucune réponse n'a correct=true → on retombe sur le 1er id de réponse ("a").
    assert out["correct"] == "a"


def test_convert_uses_default_meta_for_unknown_slug():
    mod = AwarenessModule(
        slug="slug-inconnu-xyz",
        title="X",
        quiz_yaml=_quiz_yaml(),
        estimated_duration_minutes=5,
        description="d",
    )
    out = _awareness_module_to_training(mod)
    assert out is not None
    assert out["icon"] == "school"
    assert out["color"] == "cyan"


def test_convert_uses_slug_meta_and_defaults_duration():
    mod = AwarenessModule(
        slug="ransomware",
        title="Ransomware",
        quiz_yaml=_quiz_yaml(),
        estimated_duration_minutes=None,  # → défaut 5
        description=None,  # → défaut ""
    )
    out = _awareness_module_to_training(mod)
    assert out is not None
    assert out["id"] == "awareness_ransomware"
    assert out["icon"] == "bug_report"
    assert out["color"] == "red"
    assert out["duration_min"] == 5
    assert out["description"] == ""


def test_convert_returns_none_on_corrupt_yaml_structure():
    # answers = chaîne → a["id"] lève TypeError, capturé → None.
    bad = textwrap.dedent(
        """\
        questions:
          - id: q1
            text: "Corrompu ?"
            answers: "pas une liste de dicts"
        """
    )
    mod = AwarenessModule(slug="ransomware", title="X", quiz_yaml=bad)
    assert _awareness_module_to_training(mod) is None


# ── _load_all_modules via GET /training/modules (branche awareness) ─────────────


async def test_modules_includes_awareness_module(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    r = await auth_client.get(f"{BASE}/training/modules")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()}
    # 5 modules legacy + le module awareness converti.
    assert "awareness_ransomware" in ids
    assert len(ids) == 6


async def test_modules_excludes_configured_awareness_slugs(auth_client, db_session):
    prog = await _seed_program(db_session)
    # "mfa" est dans _AWARENESS_EXCLUDED_SLUGS → jamais ajouté.
    await _seed_module(db_session, prog, slug="mfa", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    r = await auth_client.get(f"{BASE}/training/modules")
    assert r.status_code == 200
    ids = {m["id"] for m in r.json()}
    assert "awareness_mfa" not in ids
    assert len(ids) == 5  # uniquement les legacy


async def test_modules_skips_inactive_awareness_module(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml(), is_active=False)
    await db_session.commit()

    r = await auth_client.get(f"{BASE}/training/modules")
    ids = {m["id"] for m in r.json()}
    assert "awareness_ransomware" not in ids
    assert len(ids) == 5


async def test_modules_skips_awareness_without_quiz(auth_client, db_session):
    prog = await _seed_program(db_session)
    # quiz_yaml=None → _awareness_module_to_training renvoie None → non ajouté.
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=None)
    await db_session.commit()

    r = await auth_client.get(f"{BASE}/training/modules")
    ids = {m["id"] for m in r.json()}
    assert "awareness_ransomware" not in ids
    assert len(ids) == 5


async def test_modules_ignored_when_program_slug_mismatch(auth_client, db_session):
    # Un programme sur un autre slug ne doit pas être chargé.
    prog = await _seed_program(db_session, slug="autre-programme")
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    r = await auth_client.get(f"{BASE}/training/modules")
    ids = {m["id"] for m in r.json()}
    assert "awareness_ransomware" not in ids
    assert len(ids) == 5


# ── complete_module sur un module awareness ─────────────────────────────────────


async def test_complete_awareness_module_correct_persists(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    r = await auth_client.post(
        f"{BASE}/training/modules/awareness_ransomware/complete",
        json={"answer": "b"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["correct"] is True
    assert body["correct_answer"] == "b"
    assert "Explication" in body["explanation"]

    # Progression persistée en DB pour l'utilisateur connecté.
    rows = (
        (
            await db_session.execute(
                select(TrainingProgress).where(TrainingProgress.module_id == "awareness_ransomware")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


async def test_complete_awareness_module_wrong_answer_not_persisted(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    r = await auth_client.post(
        f"{BASE}/training/modules/awareness_ransomware/complete",
        json={"answer": "a"},
    )
    assert r.status_code == 200
    assert r.json()["correct"] is False

    rows = (
        (
            await db_session.execute(
                select(TrainingProgress).where(TrainingProgress.module_id == "awareness_ransomware")
            )
        )
        .scalars()
        .all()
    )
    assert rows == []


async def test_complete_unknown_module_returns_404(auth_client):
    r = await auth_client.post(
        f"{BASE}/training/modules/awareness_inexistant/complete",
        json={"answer": "b"},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "Module introuvable"


async def test_complete_module_idempotent_no_duplicate(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    for _ in range(2):
        r = await auth_client.post(
            f"{BASE}/training/modules/awareness_ransomware/complete",
            json={"answer": "b"},
        )
        assert r.status_code == 200

    rows = (
        (
            await db_session.execute(
                select(TrainingProgress).where(TrainingProgress.module_id == "awareness_ransomware")
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1


# ── Autorisation : endpoints protégés ───────────────────────────────────────────


async def test_modules_requires_auth(http_client):
    r = await http_client.get(f"{BASE}/training/modules")
    assert r.status_code == 401


async def test_progress_requires_auth(http_client):
    r = await http_client.get(f"{BASE}/training/progress")
    assert r.status_code == 401


async def test_complete_requires_auth(http_client):
    r = await http_client.post(f"{BASE}/training/modules/phishing/complete", json={"answer": "b"})
    assert r.status_code == 401


# ── get_progress : total inclut les modules awareness + isolation par user ──────


async def test_progress_total_counts_awareness_modules(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", position=0, quiz_yaml=_quiz_yaml())
    await _seed_module(db_session, prog, slug="rgpd-essentiel", position=1, quiz_yaml=_quiz_yaml())
    await db_session.commit()

    r = await auth_client.get(f"{BASE}/training/progress")
    assert r.status_code == 200
    body = r.json()
    # 5 legacy + 2 awareness.
    assert body["total"] == 7
    assert body["completed"] == 0
    assert body["percentage"] == 0


async def test_progress_reflects_completion_and_isolation(auth_client, db_session):
    prog = await _seed_program(db_session)
    await _seed_module(db_session, prog, slug="ransomware", quiz_yaml=_quiz_yaml())
    await db_session.commit()

    # Un autre utilisateur avec sa propre progression ne doit pas polluer le total.
    other = User(email="other@test.com", hashed_password="x", is_active=True)
    db_session.add(other)
    await db_session.flush()
    db_session.add(TrainingProgress(user_id=other.id, module_id="phishing"))
    await db_session.commit()

    # L'utilisateur courant complète 1 module.
    await auth_client.post(f"{BASE}/training/modules/phishing/complete", json={"answer": "b"})

    r = await auth_client.get(f"{BASE}/training/progress")
    body = r.json()
    assert body["completed"] == 1  # isolé : ne compte pas la progression de "other"
    assert body["total"] == 6  # 5 legacy + 1 awareness
    assert "phishing" in body["completed_ids"]
    assert "awareness_ransomware" not in body["completed_ids"]
