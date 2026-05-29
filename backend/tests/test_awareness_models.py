"""
Tests d'intégration — modèles SQLAlchemy du module Sensibilisation.

Couvre :
  - Création et persistance des 10 modèles
  - Contraintes (unique badge par learner, cascade delete)
  - Valeurs par défaut
  - Relation enrollment → certificate (one-to-one)
"""

import pytest
from sqlalchemy import select

from app.models.awareness_badge import AwarenessBadge
from app.models.awareness_certificate import AwarenessCertificate
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_learner_badge import AwarenessLearnerBadge
from app.models.awareness_module import AwarenessModule
from app.models.awareness_organization import AwarenessOrganization
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress
from app.models.awareness_quiz_attempt import AwarenessQuizAttempt
from app.models.user import User

# ── helpers ────────────────────────────────────────────────────────────────────


async def _create_user(db, email="owner@test.com"):
    user = User(
        email=email,
        hashed_password="hashed",
        is_active=True,
    )
    db.add(user)
    await db.flush()
    return user


async def _create_org(db, user):
    org = AwarenessOrganization(
        owner_user_id=user.id,
        name="Acme Corp",
        max_learners=50,
    )
    db.add(org)
    await db.flush()
    return org


async def _create_learner(db, org, email="alice@acme.com"):
    learner = AwarenessLearner(
        organization_id=org.id,
        email=email,
        first_name="Alice",
        last_name="Dupont",
    )
    db.add(learner)
    await db.flush()
    return learner


async def _create_program(db, slug="nis2-test"):
    prog = AwarenessProgram(
        slug=slug,
        title="NIS2 Test",
        passing_score=60,
        certificate_validity_months=12,
        version="1.0",
    )
    db.add(prog)
    await db.flush()
    return prog


async def _create_module(db, prog, slug="phishing"):
    mod = AwarenessModule(
        program_id=prog.id,
        slug=slug,
        title="Phishing Bases",
        position=1,
        xp_points=10,
    )
    db.add(mod)
    await db.flush()
    return mod


async def _create_enrollment(db, learner, prog, org):
    enroll = AwarenessEnrollment(
        learner_id=learner.id,
        program_id=prog.id,
        organization_id=org.id,
        status="pending",
    )
    db.add(enroll)
    await db.flush()
    return enroll


# ── AwarenessOrganization ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_organization_created(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessOrganization).where(AwarenessOrganization.id == org.id)
    )
    fetched = result.scalar_one()
    assert fetched.name == "Acme Corp"
    assert fetched.max_learners == 50
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_organization_default_values(db_session):
    user = await _create_user(db_session)
    org = AwarenessOrganization(owner_user_id=user.id, name="Test Org")
    db_session.add(org)
    await db_session.flush()

    assert org.is_active is True
    assert org.max_learners == 10


# ── AwarenessLearner ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_learner_created(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessLearner).where(AwarenessLearner.id == learner.id)
    )
    fetched = result.scalar_one()
    assert fetched.email == "alice@acme.com"
    assert fetched.preferred_language == "fr"
    assert fetched.is_active is True
    assert fetched.anonymized_at is None


# ── AwarenessProgram ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_program_slug_unique(db_session):
    from sqlalchemy.exc import IntegrityError

    await _create_program(db_session, slug="unique-slug")
    await db_session.commit()

    prog2 = AwarenessProgram(slug="unique-slug", title="Doublon", version="1.0")
    db_session.add(prog2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_program_default_values(db_session):
    prog = AwarenessProgram(slug="default-prog", title="Test", version="1.0")
    db_session.add(prog)
    await db_session.flush()

    assert prog.language == "fr"
    assert prog.passing_score == 60
    assert prog.certificate_validity_months == 12
    assert prog.is_active is True


# ── AwarenessModule ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_module_linked_to_program(db_session):
    prog = await _create_program(db_session)
    mod = await _create_module(db_session, prog)
    await db_session.commit()

    result = await db_session.execute(select(AwarenessModule).where(AwarenessModule.id == mod.id))
    fetched = result.scalar_one()
    assert fetched.program_id == prog.id
    assert fetched.xp_points == 10
    assert fetched.quiz_max_attempts == 3


# ── AwarenessEnrollment ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_enrollment_default_status(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    prog = await _create_program(db_session)
    enroll = await _create_enrollment(db_session, learner, prog, org)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessEnrollment).where(AwarenessEnrollment.id == enroll.id)
    )
    fetched = result.scalar_one()
    assert fetched.status == "pending"
    assert fetched.completion_pct == 0.0
    assert fetched.xp_earned == 0


# ── AwarenessProgress ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_progress_created(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    prog = await _create_program(db_session)
    mod = await _create_module(db_session, prog)
    enroll = await _create_enrollment(db_session, learner, prog, org)

    progress = AwarenessProgress(
        enrollment_id=enroll.id,
        module_id=mod.id,
        status="in_progress",
        time_spent_seconds=45,
    )
    db_session.add(progress)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessProgress).where(AwarenessProgress.enrollment_id == enroll.id)
    )
    fetched = result.scalar_one()
    assert fetched.status == "in_progress"
    assert fetched.time_spent_seconds == 45
    assert fetched.video_resume_position == 0


# ── AwarenessQuizAttempt ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_quiz_attempt_created(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    prog = await _create_program(db_session)
    mod = await _create_module(db_session, prog)

    attempt = AwarenessQuizAttempt(
        learner_id=learner.id,
        module_id=mod.id,
        attempt_number=1,
        score=80,
        result="passed",
        duration_seconds=120,
    )
    db_session.add(attempt)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessQuizAttempt).where(AwarenessQuizAttempt.learner_id == learner.id)
    )
    fetched = result.scalar_one()
    assert fetched.score == 80
    assert fetched.result == "passed"


# ── AwarenessCertificate ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_certificate_created(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    prog = await _create_program(db_session)
    enroll = await _create_enrollment(db_session, learner, prog, org)

    cert = AwarenessCertificate(
        enrollment_id=enroll.id,
        learner_id=learner.id,
        public_id="CERT-2026-ABCD01",
        verification_token="tok123abc",
        signature_hash="a" * 64,
        frozen_data_json='{"learner": "alice"}',
    )
    db_session.add(cert)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessCertificate).where(AwarenessCertificate.public_id == "CERT-2026-ABCD01")
    )
    fetched = result.scalar_one()
    assert fetched.is_revoked is False
    assert fetched.verification_count == 0
    assert fetched.learner_id == learner.id


@pytest.mark.asyncio
async def test_certificate_public_id_unique(db_session):
    from sqlalchemy.exc import IntegrityError

    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    prog = await _create_program(db_session)
    enroll = await _create_enrollment(db_session, learner, prog, org)

    cert1 = AwarenessCertificate(
        enrollment_id=enroll.id,
        learner_id=learner.id,
        public_id="CERT-DUPE",
        verification_token="tok-unique-1",
        signature_hash="b" * 64,
        frozen_data_json="{}",
    )
    db_session.add(cert1)
    await db_session.flush()

    cert2 = AwarenessCertificate(
        enrollment_id=enroll.id,
        learner_id=learner.id,
        public_id="CERT-DUPE",
        verification_token="tok-unique-2",
        signature_hash="c" * 64,
        frozen_data_json="{}",
    )
    db_session.add(cert2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ── AwarenessBadge + AwarenessLearnerBadge ────────────────────────────────────


@pytest.mark.asyncio
async def test_badge_created(db_session):
    badge = AwarenessBadge(
        slug="first_step",
        name="Premier pas",
        icon="🏅",
        xp_bonus=5,
        category="engagement",
    )
    db_session.add(badge)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessBadge).where(AwarenessBadge.slug == "first_step")
    )
    fetched = result.scalar_one()
    assert fetched.xp_bonus == 5
    assert fetched.is_active is True


@pytest.mark.asyncio
async def test_learner_badge_unique_constraint(db_session):
    from sqlalchemy.exc import IntegrityError

    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)

    badge = AwarenessBadge(slug="unique-badge", name="Badge", icon="🎖️", category="engagement")
    db_session.add(badge)
    await db_session.flush()

    lb1 = AwarenessLearnerBadge(learner_id=learner.id, badge_id=badge.id)
    db_session.add(lb1)
    await db_session.flush()

    lb2 = AwarenessLearnerBadge(learner_id=learner.id, badge_id=badge.id)
    db_session.add(lb2)
    with pytest.raises(IntegrityError):
        await db_session.flush()


# ── cascade delete ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_organization_cascades_to_learners(db_session):
    user = await _create_user(db_session)
    org = await _create_org(db_session, user)
    learner = await _create_learner(db_session, org)
    await db_session.commit()

    learner_id = learner.id
    await db_session.delete(org)
    await db_session.commit()

    result = await db_session.execute(
        select(AwarenessLearner).where(AwarenessLearner.id == learner_id)
    )
    assert result.scalar_one_or_none() is None
