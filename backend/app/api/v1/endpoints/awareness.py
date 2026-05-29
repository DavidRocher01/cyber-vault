"""
Awareness module — Sprints 2 & 3.

Sprint 2 — Organisations, learners, CSV import, magic-link auth.
Sprint 3 — Programmes, inscriptions, progression (start/heartbeat/complete), dashboard learner.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_learner, get_current_user
from app.models.awareness_badge import AwarenessBadge
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_learner_badge import AwarenessLearnerBadge
from app.models.awareness_module import AwarenessModule
from app.models.awareness_organization import AwarenessOrganization
from app.models.awareness_program import AwarenessProgram
from app.models.awareness_progress import AwarenessProgress
from app.models.user import User
from app.schemas.awareness import (
    AwarenessCertificateOut,
    AwarenessEnrollmentOut,
    AwarenessLearnerCreate,
    AwarenessLearnerOut,
    AwarenessLearnerUpdate,
    AwarenessModuleOut,
    AwarenessOrganizationCreate,
    AwarenessOrganizationOut,
    AwarenessOrganizationStats,
    AwarenessOrganizationUpdate,
    AwarenessProgramOut,
    AwarenessProgressOut,
    BadgeOut,
    CompleteModuleIn,
    ConsultantDashboardOut,
    CsvImportResult,
    HeartbeatIn,
    LeaderboardEntry,
    LearnerDashboard,
    LearnerLevelOut,
    LearnerModuleProgress,
    LearnerSession,
    MagicLinkRequest,
    OrgAdminDashboardOut,
    QuizResultOut,
    QuizStartOut,
    QuizSubmitIn,
)
from app.services.awareness_csv_import import import_learners_from_csv
from app.services.awareness_magic_link import (
    create_learner_jwt,
    issue_magic_link,
    verify_magic_link,
)
from app.services.awareness_progression import (
    complete_module,
    enroll_learner,
    heartbeat,
    start_module,
)
from app.services.awareness_quiz_engine import start_quiz, submit_quiz
from app.services.email_service import send_awareness_magic_link

router = APIRouter(prefix="/awareness", tags=["awareness"])


# ── helpers ────────────────────────────────────────────────────────────────────


async def _get_org_or_404(org_id: int, user: User, db: AsyncSession) -> AwarenessOrganization:
    result = await db.execute(
        select(AwarenessOrganization).where(
            AwarenessOrganization.id == org_id,
            AwarenessOrganization.owner_user_id == user.id,
        )
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=404, detail="Organisation introuvable.")
    return org


async def _get_learner_or_404(learner_id: int, org_id: int, db: AsyncSession) -> AwarenessLearner:
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.id == learner_id,
            AwarenessLearner.organization_id == org_id,
        )
    )
    learner = result.scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=404, detail="Learner introuvable.")
    return learner


# ── Organizations ──────────────────────────────────────────────────────────────


@router.post("/organizations", response_model=AwarenessOrganizationOut, status_code=201)
async def create_organization(
    payload: AwarenessOrganizationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationOut:
    org = AwarenessOrganization(
        owner_user_id=current_user.id,
        name=payload.name,
        siret=payload.siret,
        sector=payload.sector,
        max_learners=payload.max_learners,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return AwarenessOrganizationOut.model_validate(org)


@router.get("/organizations", response_model=list[AwarenessOrganizationStats])
async def list_organizations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessOrganizationStats]:
    result = await db.execute(
        select(AwarenessOrganization).where(AwarenessOrganization.owner_user_id == current_user.id)
    )
    orgs = result.scalars().all()

    out = []
    for org in orgs:
        learner_count = (
            await db.execute(
                select(func.count(AwarenessLearner.id)).where(
                    AwarenessLearner.organization_id == org.id,
                    AwarenessLearner.is_active == True,
                )
            )
        ).scalar_one()
        stats = AwarenessOrganizationStats.model_validate(org)
        stats.learner_count = learner_count
        out.append(stats)
    return out


@router.get("/organizations/{org_id}", response_model=AwarenessOrganizationStats)
async def get_organization(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationStats:
    org = await _get_org_or_404(org_id, current_user, db)
    learner_count = (
        await db.execute(
            select(func.count(AwarenessLearner.id)).where(
                AwarenessLearner.organization_id == org.id,
                AwarenessLearner.is_active == True,
            )
        )
    ).scalar_one()
    stats = AwarenessOrganizationStats.model_validate(org)
    stats.learner_count = learner_count
    return stats


@router.patch("/organizations/{org_id}", response_model=AwarenessOrganizationOut)
async def update_organization(
    org_id: int,
    payload: AwarenessOrganizationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessOrganizationOut:
    org = await _get_org_or_404(org_id, current_user, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(org, field, value)
    await db.commit()
    await db.refresh(org)
    return AwarenessOrganizationOut.model_validate(org)


# ── Learners ───────────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/learners",
    response_model=AwarenessLearnerOut,
    status_code=201,
)
async def create_learner(
    org_id: int,
    payload: AwarenessLearnerCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessLearnerOut:
    org = await _get_org_or_404(org_id, current_user, db)

    # Check quota
    count = (
        await db.execute(
            select(func.count(AwarenessLearner.id)).where(
                AwarenessLearner.organization_id == org.id,
                AwarenessLearner.is_active == True,
            )
        )
    ).scalar_one()
    if count >= org.max_learners:
        raise HTTPException(
            status_code=422,
            detail=f"Quota atteint ({org.max_learners} learners max).",
        )

    # Check duplicate
    existing = (
        await db.execute(
            select(AwarenessLearner).where(
                AwarenessLearner.organization_id == org_id,
                AwarenessLearner.email == payload.email,
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=409, detail="Email déjà enregistré dans cette organisation."
        )

    learner = AwarenessLearner(
        organization_id=org_id,
        email=str(payload.email),
        first_name=payload.first_name,
        last_name=payload.last_name,
        department=payload.department,
        job_title=payload.job_title,
        preferred_language=payload.preferred_language,
    )
    db.add(learner)
    await db.commit()
    await db.refresh(learner)
    return AwarenessLearnerOut.model_validate(learner)


@router.get("/organizations/{org_id}/learners", response_model=list[AwarenessLearnerOut])
async def list_learners(
    org_id: int,
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessLearnerOut]:
    await _get_org_or_404(org_id, current_user, db)
    query = select(AwarenessLearner).where(AwarenessLearner.organization_id == org_id)
    if active_only:
        query = query.where(AwarenessLearner.is_active == True)
    result = await db.execute(query)
    return [AwarenessLearnerOut.model_validate(row) for row in result.scalars().all()]


@router.patch(
    "/organizations/{org_id}/learners/{learner_id}",
    response_model=AwarenessLearnerOut,
)
async def update_learner(
    org_id: int,
    learner_id: int,
    payload: AwarenessLearnerUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AwarenessLearnerOut:
    await _get_org_or_404(org_id, current_user, db)
    learner = await _get_learner_or_404(learner_id, org_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(learner, field, value)
    await db.commit()
    await db.refresh(learner)
    return AwarenessLearnerOut.model_validate(learner)


# ── CSV Import ─────────────────────────────────────────────────────────────────


@router.post(
    "/organizations/{org_id}/learners/import-csv",
    response_model=CsvImportResult,
)
async def import_learners_csv(
    org_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CsvImportResult:
    await _get_org_or_404(org_id, current_user, db)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Fichier CSV requis.")

    content = await file.read()
    if len(content) > 2 * 1024 * 1024:  # 2 MB max
        raise HTTPException(status_code=422, detail="Fichier trop volumineux (max 2 MB).")

    return await import_learners_from_csv(db, org_id, content)


# ── Magic-link auth ────────────────────────────────────────────────────────────


@router.post("/auth/magic-link", status_code=202)
async def request_magic_link(
    payload: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Generate a magic link for a learner. Always returns 202 to avoid email enumeration.
    In production the raw token is sent by email; here it's returned for dev convenience.
    """
    result = await issue_magic_link(db, str(payload.email), payload.organization_id)
    if result is None:
        return {"message": "Si l'email existe, un lien de connexion vous a été envoyé."}

    learner, raw_token = result

    org_result = await db.execute(
        select(AwarenessOrganization).where(AwarenessOrganization.id == learner.organization_id)
    )
    org = org_result.scalar_one_or_none()
    org_name = org.name if org else "votre organisation"

    login_url = f"{settings.FRONTEND_URL}/awareness/login?token={raw_token}"
    try:
        send_awareness_magic_link(
            to_email=str(learner.email),
            first_name=learner.first_name,
            org_name=org_name,
            login_url=login_url,
        )
    except Exception:
        pass  # Ne pas bloquer si l'envoi échoue

    return {"message": "Si l'email existe, un lien de connexion vous a été envoyé."}


@router.get("/auth/verify", response_model=LearnerSession)
async def verify_magic_link_token(
    token: str = Query(..., min_length=10),
    db: AsyncSession = Depends(get_db),
) -> LearnerSession:
    learner = await verify_magic_link(db, token)
    if learner is None:
        raise HTTPException(
            status_code=401,
            detail="Lien invalide ou expiré. Demandez un nouveau lien.",
        )
    jwt_token = create_learner_jwt(learner)
    return LearnerSession(
        learner_id=learner.id,
        organization_id=learner.organization_id,
        email=learner.email,
        first_name=learner.first_name,
        last_name=learner.last_name,
        access_token=jwt_token,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 3 — Programmes, inscriptions, progression
# ══════════════════════════════════════════════════════════════════════════════

# ── Programmes (public pour les learners authentifiés) ─────────────────────────


@router.get("/programs", response_model=list[AwarenessProgramOut])
async def list_programs(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> list[AwarenessProgramOut]:
    """Liste les programmes actifs disponibles pour un learner."""
    result = await db.execute(select(AwarenessProgram).where(AwarenessProgram.is_active == True))
    programs = result.scalars().all()
    out = []
    for prog in programs:
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
        prog_out = AwarenessProgramOut.model_validate(prog)
        prog_out.modules = [AwarenessModuleOut.model_validate(m) for m in mods]
        out.append(prog_out)
    return out


@router.get("/programs/{program_id}", response_model=AwarenessProgramOut)
async def get_program(
    program_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessProgramOut:
    prog = (
        await db.execute(
            select(AwarenessProgram).where(
                AwarenessProgram.id == program_id, AwarenessProgram.is_active == True
            )
        )
    ).scalar_one_or_none()
    if prog is None:
        raise HTTPException(status_code=404, detail="Programme introuvable.")
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
    prog_out = AwarenessProgramOut.model_validate(prog)
    prog_out.modules = [AwarenessModuleOut.model_validate(m) for m in mods]
    return prog_out


# ── Enrollments ────────────────────────────────────────────────────────────────


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


# ── Progression ────────────────────────────────────────────────────────────────


@router.post(
    "/enrollments/{enrollment_id}/modules/{module_id}/start", response_model=AwarenessProgressOut
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


# ── Dashboard learner ──────────────────────────────────────────────────────────


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

    prog_out = AwarenessProgramOut.model_validate(prog)
    prog_out.modules = [AwarenessModuleOut.model_validate(m) for m in mods]

    return LearnerDashboard(
        enrollment=AwarenessEnrollmentOut.model_validate(enrollment),
        program=prog_out,
        modules_progress=modules_progress,
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 4 — Moteur de quiz
# ══════════════════════════════════════════════════════════════════════════════


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


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 5 — Attestations (certificats)
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/enrollments/{enrollment_id}/certificate", response_model=AwarenessCertificateOut)
async def get_certificate(
    enrollment_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> AwarenessCertificateOut:
    """Retourne les métadonnées du certificat d'une inscription complétée."""
    from app.models.awareness_certificate import AwarenessCertificate

    cert = (
        await db.execute(
            select(AwarenessCertificate).where(
                AwarenessCertificate.enrollment_id == enrollment_id,
                AwarenessCertificate.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if cert is None:
        raise HTTPException(
            status_code=404, detail="Certificat introuvable — programme non complété."
        )
    return AwarenessCertificateOut.model_validate(cert)


@router.get("/enrollments/{enrollment_id}/certificate/download")
async def download_certificate_pdf(
    enrollment_id: int,
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
):
    """Télécharge le PDF du certificat."""
    from fastapi.responses import Response

    from app.models.awareness_certificate import AwarenessCertificate
    from app.services.awareness_certificate_service import generate_certificate_pdf

    cert = (
        await db.execute(
            select(AwarenessCertificate).where(
                AwarenessCertificate.enrollment_id == enrollment_id,
                AwarenessCertificate.learner_id == learner.id,
            )
        )
    ).scalar_one_or_none()
    if cert is None:
        raise HTTPException(status_code=404, detail="Certificat introuvable.")

    frozen = __import__("json").loads(cert.frozen_data_json)
    pdf_bytes = generate_certificate_pdf(cert, frozen)
    filename = f"attestation-{cert.public_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 6 — Gamification (XP, niveau, badges, leaderboard)
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/me/level", response_model=LearnerLevelOut)
async def get_my_level(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> LearnerLevelOut:
    """Retourne le niveau et les XP totaux du learner authentifié."""
    from app.services.awareness_gamification import compute_level, compute_total_xp

    total_xp = await compute_total_xp(db, learner.id)
    level = compute_level(total_xp)
    return LearnerLevelOut(**level)


@router.get("/me/badges", response_model=list[BadgeOut])
async def get_my_badges(
    learner: AwarenessLearner = Depends(get_current_learner),
    db: AsyncSession = Depends(get_db),
) -> list[BadgeOut]:
    """Retourne les badges gagnés par le learner authentifié."""
    result = await db.execute(
        select(AwarenessLearnerBadge, AwarenessBadge)
        .join(AwarenessBadge, AwarenessBadge.id == AwarenessLearnerBadge.badge_id)
        .where(AwarenessLearnerBadge.learner_id == learner.id)
        .order_by(AwarenessLearnerBadge.earned_at.desc())
    )
    rows = result.all()
    out = []
    for lb, badge in rows:
        b = BadgeOut.model_validate(badge)
        b.earned_at = lb.earned_at
        out.append(b)
    return out


@router.get("/organizations/{org_id}/leaderboard", response_model=list[LeaderboardEntry])
async def get_leaderboard_endpoint(
    org_id: int,
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[LeaderboardEntry]:
    """Classement des learners par XP total (noms anonymisés). Accès admin de l'org."""
    await _get_org_or_404(org_id, current_user, db)
    from app.services.awareness_gamification import get_leaderboard

    rows = await get_leaderboard(db, org_id, limit)
    return [LeaderboardEntry(**r) for r in rows]


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 7 — Multi-tenancy dashboards
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/consultant/dashboard", response_model=ConsultantDashboardOut)
async def consultant_dashboard_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConsultantDashboardOut:
    """
    Vue agrégée RSSI consultant : toutes ses organisations clientes,
    KPIs globaux, alertes.
    """
    from app.services.awareness_dashboard import consultant_dashboard

    data = await consultant_dashboard(db, current_user.id)
    return ConsultantDashboardOut(**data)


@router.get("/organizations/{org_id}/admin-dashboard", response_model=OrgAdminDashboardOut)
async def org_admin_dashboard_endpoint(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OrgAdminDashboardOut:
    """
    Vue détaillée admin : funnel engagement, stats par programme,
    learners à risque (initiales seulement — RGPD).
    """
    await _get_org_or_404(org_id, current_user, db)
    from app.services.awareness_dashboard import org_admin_dashboard

    data = await org_admin_dashboard(db, org_id)
    return OrgAdminDashboardOut(**data)


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 8 — Rapport NIS2 compliance
# ══════════════════════════════════════════════════════════════════════════════


@router.get("/organizations/{org_id}/nis2-report")
async def get_nis2_report(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retourne les métriques NIS2 Article 21 en JSON."""
    await _get_org_or_404(org_id, current_user, db)
    from app.services.awareness_nis2_report import build_nis2_report

    return await build_nis2_report(db, org_id)


@router.get("/organizations/{org_id}/nis2-report/pdf")
async def download_nis2_report_pdf(
    org_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Génère et télécharge le rapport PDF NIS2."""
    from fastapi.responses import Response

    from app.services.awareness_nis2_report import (
        build_nis2_report,
        generate_nis2_report_pdf,
    )

    await _get_org_or_404(org_id, current_user, db)
    data = await build_nis2_report(db, org_id)
    pdf_bytes = generate_nis2_report_pdf(
        data["org_name"],
        data["requirements"],
        data["global_score"],
        data["metrics"],
        data["certificate_count"],
        data["generated_at"],
    )
    filename = f"rapport-nis2-{org_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Sprint 9 — Intégration phishing (webhook auto-enrôlement)
# ══════════════════════════════════════════════════════════════════════════════


@router.post("/internal/phishing-click", status_code=202)
async def phishing_click_webhook(
    learner_email: str,
    organization_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Webhook interne déclenché quand un learner clique sur un lien de simulation phishing.
    Auto-enrôle le learner dans le module de remédiation post-clic (bienveillant, 3 min).
    Aucune authentification — appelé uniquement par le module phishing interne.
    """
    learner = (
        await db.execute(
            select(AwarenessLearner).where(
                AwarenessLearner.email == learner_email,
                AwarenessLearner.organization_id == organization_id,
                AwarenessLearner.is_active == True,
            )
        )
    ).scalar_one_or_none()

    if learner is None:
        return {"enrolled": False, "reason": "learner not found"}

    # Find a remediation program (slug contains "remediation" or "post-clic")
    from app.models.awareness_program import AwarenessProgram

    remediation_prog = (
        await db.execute(
            select(AwarenessProgram)
            .where(
                AwarenessProgram.is_active == True,
                AwarenessProgram.slug.contains("remediation"),
            )
            .limit(1)
        )
    ).scalar_one_or_none()

    if remediation_prog is None:
        return {"enrolled": False, "reason": "no remediation program configured"}

    from app.services.awareness_progression import enroll_learner

    enrollment = await enroll_learner(db, learner, remediation_prog.id)
    return {
        "enrolled": True,
        "enrollment_id": enrollment.id,
        "program_title": remediation_prog.title,
    }
