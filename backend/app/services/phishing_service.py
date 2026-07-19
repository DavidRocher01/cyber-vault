"""
Phishing simulation engine — homemade, no GoPhish required.

Architecture:
  - Emails sent via Resend (already in requirements) with per-target tracking IDs
  - Tracking pixel / click / landing pages served by this FastAPI backend
  - APScheduler sends emails in batches (PHISHING_BATCH_SIZE every 15 min)
  - Results stored directly in phishing_targets rows (no external API polling)

URL scheme for tracking routes (all public, no auth):
  GET  /phishing/t/{tracking_id}/px    → 1x1 transparent GIF, marks "opened"
  GET  /phishing/t/{tracking_id}/c     → redirects to landing page, marks "clicked"
  GET  /phishing/t/{tracking_id}/l     → serves phishing landing page HTML
  POST /phishing/t/{tracking_id}/s     → records form submission, returns awareness page
"""

import asyncio
import csv
import io
import json
import secrets
import uuid
from datetime import UTC, datetime

import resend
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.models.enums import CampaignStatus, TargetStatus
from app.models.phishing import (
    PhishingCampaign,
    PhishingDomainVerification,
    PhishingTarget,
)
from app.models.user import User
from app.services.phishing_templates import (
    _DEFAULT_SCENARIO_KEY,
    _SCENARIO_TEMPLATES,
    _dynamic_ctx,
)
from app.services.phishing_templates import (
    get_awareness_html as get_awareness_html,  # re-export (facade service)
)
from app.services.phishing_templates import (
    get_expired_html as get_expired_html,
)
from app.services.phishing_templates import (
    get_landing_html as get_landing_html,
)
from app.services.phishing_templates import (
    get_pixel_gif as get_pixel_gif,
)

# Prevents two concurrent batch runs from double-sending (APScheduler + create_task on launch)
_batch_lock = asyncio.Lock()


async def request_domain_verification(
    user_id: int, domain: str, db: AsyncSession
) -> PhishingDomainVerification:
    result = await db.execute(
        select(PhishingDomainVerification).where(
            PhishingDomainVerification.user_id == user_id,
            PhishingDomainVerification.domain == domain,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.verified:
        return existing

    token = f"rocher-verify-{secrets.token_urlsafe(16)}"
    if existing:
        existing.verification_token = token
        existing.verified = False
        existing.verified_at = None
    else:
        existing = PhishingDomainVerification(
            user_id=user_id,
            domain=domain,
            verification_token=token,
        )
        db.add(existing)
    await db.flush()
    await db.refresh(existing)
    return existing


async def check_domain_verification(record: PhishingDomainVerification, db: AsyncSession) -> bool:
    if record.verified:
        return True
    if settings.APP_ENV == "development":
        record.verified = True
        record.verified_at = datetime.now(UTC)
        await db.flush()
        return True
    try:
        import dns.resolver

        answers = dns.resolver.resolve(f"_rocher-verify.{record.domain}", "TXT", lifetime=5.0)
        for rdata in answers:
            for txt_string in rdata.strings:
                if txt_string.decode("utf-8") == record.verification_token:
                    record.verified = True
                    record.verified_at = datetime.now(UTC)
                    await db.flush()
                    return True
    except Exception as exc:
        logger.debug(f"DNS TXT check failed for {record.domain}: {exc}")
    return False


async def get_domain_verification(
    user_id: int, domain: str, db: AsyncSession
) -> PhishingDomainVerification | None:
    """Retourne la demande de vérification d'un domaine pour un utilisateur (ou None)."""
    result = await db.execute(
        select(PhishingDomainVerification).where(
            PhishingDomainVerification.user_id == user_id,
            PhishingDomainVerification.domain == domain,
        )
    )
    return result.scalar_one_or_none()


async def is_domain_verified(user_id: int, domain: str, db: AsyncSession) -> bool:
    """True si l'utilisateur possède une vérification RÉUSSIE pour ce domaine."""
    result = await db.execute(
        select(PhishingDomainVerification.id).where(
            PhishingDomainVerification.user_id == user_id,
            PhishingDomainVerification.domain == domain,
            PhishingDomainVerification.verified.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Campaign CRUD
# ---------------------------------------------------------------------------


async def get_campaigns(
    user_id: int,
    db: AsyncSession,
    *,
    rssi_client_id: int | None = None,
    company_only: bool = False,
) -> list[PhishingCampaign]:
    """Campagnes du propriétaire, filtrées par mode :
    - rssi_client_id renseigné → campagnes de ce client (mode consultant) ;
    - company_only=True → campagnes sans client (mode entreprise directe) ;
    - sinon → toutes celles du propriétaire.
    """
    query = select(PhishingCampaign).where(PhishingCampaign.user_id == user_id)
    if rssi_client_id is not None:
        query = query.where(PhishingCampaign.rssi_client_id == rssi_client_id)
    elif company_only:
        query = query.where(PhishingCampaign.rssi_client_id.is_(None))
    result = await db.execute(query.order_by(PhishingCampaign.created_at.desc()))
    return list(result.scalars().all())


async def get_campaign(campaign_id: int, user_id: int, db: AsyncSession) -> PhishingCampaign | None:
    result = await db.execute(
        select(PhishingCampaign).where(
            PhishingCampaign.id == campaign_id,
            PhishingCampaign.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_targets(campaign_id: int, db: AsyncSession) -> list[PhishingTarget]:
    """Cibles d'une campagne (ordre d'insertion)."""
    result = await db.execute(
        select(PhishingTarget)
        .where(PhishingTarget.campaign_id == campaign_id)
        .order_by(PhishingTarget.id)
    )
    return list(result.scalars().all())


async def delete_campaign(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Supprime la campagne (cibles supprimées en cascade via la relation ORM)."""
    await db.delete(campaign)


async def create_campaign(
    user_id: int,
    name: str,
    plan_tier: str,
    db: AsyncSession,
    *,
    rssi_client_id: int | None = None,
) -> PhishingCampaign:
    campaign = PhishingCampaign(
        user_id=user_id,
        name=name,
        plan_tier=plan_tier,
        status=CampaignStatus.DRAFT,
        rssi_client_id=rssi_client_id,
    )
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return campaign


async def update_campaign(
    campaign: PhishingCampaign,
    *,
    name: str | None = None,
    domain: str | None = None,
    domain_verified: bool | None = None,
    lookalike_domain: str | None = None,
    scenario_keys: list[str] | None = None,
    cgu_accepted: bool | None = None,
    scheduled_at: datetime | None = None,
    status: str | None = None,
    training_on_fail: bool | None = None,
    training_trigger: str | None = None,
    batch_size: int | None = None,
    db: AsyncSession,
) -> PhishingCampaign:
    if name is not None:
        campaign.name = name
    if domain is not None:
        campaign.domain = domain
    if domain_verified is not None:
        campaign.domain_verified = domain_verified
    if lookalike_domain is not None:
        campaign.lookalike_domain = lookalike_domain
    if scenario_keys is not None:
        campaign.scenario_keys = json.dumps(scenario_keys)
    if cgu_accepted is not None:
        campaign.cgu_accepted = cgu_accepted
    if training_on_fail is not None:
        campaign.training_on_fail = training_on_fail
    if training_trigger is not None:
        campaign.training_trigger = training_trigger
    if batch_size is not None:
        campaign.batch_size = batch_size
    if scheduled_at is not None:
        campaign.scheduled_at = scheduled_at
    if status is not None:
        campaign.status = status
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    return campaign


async def cancel_campaign(campaign: PhishingCampaign, db: AsyncSession) -> PhishingCampaign:
    """Annule une campagne : le statut "cancelled" l'exclut du batch (qui ne
    traite que scheduled/active/sending) — plus aucun email ne partira."""
    campaign.status = CampaignStatus.CANCELLED
    campaign.finished_at = datetime.now(UTC)
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    return campaign


async def _recount_targets(campaign: PhishingCampaign, db: AsyncSession) -> int:
    """Resynchronise campaign.targets_count avec le nombre réel de cibles."""
    total = (
        await db.execute(
            select(func.count(PhishingTarget.id)).where(PhishingTarget.campaign_id == campaign.id)
        )
    ).scalar() or 0
    campaign.targets_count = total
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    return total


async def upload_targets_csv(
    campaign: PhishingCampaign, csv_content: str, db: AsyncSession, *, replace: bool = False
) -> dict:
    """Importe des cibles depuis un CSV.

    - replace=False (défaut) : MERGE — ajoute les nouvelles cibles sans écraser
      les existantes, en ignorant les doublons d'email (dédup insensible à la casse).
    - replace=True : remplace toutes les cibles (ancien comportement, sur demande explicite).

    Retourne {"added", "skipped", "total"}.
    """
    if replace:
        existing = await db.execute(
            select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
        )
        for t in existing.scalars().all():
            await db.delete(t)
        await db.flush()
        seen: set[str] = set()
    else:
        rows = (
            (
                await db.execute(
                    select(PhishingTarget.email).where(PhishingTarget.campaign_id == campaign.id)
                )
            )
            .scalars()
            .all()
        )
        seen = {e.lower() for e in rows}

    reader = csv.DictReader(io.StringIO(csv_content))
    added = 0
    skipped = 0
    for row in reader:
        email = (row.get("email") or row.get("Email") or "").strip()
        if not email or "@" not in email:
            continue
        if email.lower() in seen:
            skipped += 1
            continue
        seen.add(email.lower())
        db.add(
            PhishingTarget(
                campaign_id=campaign.id,
                email=email,
                first_name=(
                    row.get("first_name") or row.get("prenom") or row.get("Prénom") or ""
                ).strip(),
                last_name=(row.get("last_name") or row.get("nom") or row.get("Nom") or "").strip()
                or None,
                department=(
                    row.get("department") or row.get("departement") or row.get("Département") or ""
                ).strip()
                or None,
            )
        )
        added += 1

    await db.flush()
    total = await _recount_targets(campaign, db)
    return {"added": added, "skipped": skipped, "total": total}


async def add_target(
    campaign: PhishingCampaign,
    *,
    email: str,
    first_name: str = "",
    last_name: str | None = None,
    department: str | None = None,
    db: AsyncSession,
) -> PhishingTarget | None:
    """Ajoute une cible unique. Retourne None si l'email existe déjà (dédup)."""
    exists = (
        await db.execute(
            select(PhishingTarget).where(
                PhishingTarget.campaign_id == campaign.id,
                func.lower(PhishingTarget.email) == email.lower(),
            )
        )
    ).scalar_one_or_none()
    if exists:
        return None
    target = PhishingTarget(
        campaign_id=campaign.id,
        email=email,
        first_name=first_name or "",
        last_name=last_name or None,
        department=department or None,
    )
    db.add(target)
    await db.flush()
    await _recount_targets(campaign, db)
    await db.refresh(target)
    return target


async def delete_target(campaign: PhishingCampaign, target_id: int, db: AsyncSession) -> bool:
    """Supprime une cible. Retourne False si introuvable pour cette campagne."""
    target = (
        await db.execute(
            select(PhishingTarget).where(
                PhishingTarget.id == target_id,
                PhishingTarget.campaign_id == campaign.id,
            )
        )
    ).scalar_one_or_none()
    if target is None:
        return False
    await db.delete(target)
    await db.flush()
    await _recount_targets(campaign, db)
    return True


# ---------------------------------------------------------------------------
# Email sending engine
# ---------------------------------------------------------------------------


def _lookalike_host(campaign: PhishingCampaign) -> str | None:
    """Host nu du domaine look-alike (sans schéma ni slash final), ou None.
    Source unique du nettoyage — utilisé par _tracking_base ET _build_email."""
    raw = campaign.lookalike_domain
    if not raw:
        return None
    raw = raw.strip()
    for scheme in ("https://", "http://"):
        if raw.startswith(scheme):
            raw = raw[len(scheme) :]
            break
    return raw.rstrip("/") or None


def _tracking_base(campaign: PhishingCampaign) -> str:
    """Determine the base URL for tracking links (look-alike or default)."""
    host = _lookalike_host(campaign)
    if host:
        return f"https://{host}"
    return settings.PHISHING_BASE_URL.rstrip("/")


def _extract_company_name(domain: str | None) -> str:
    """Extract a display-ready company name from a domain. "acme-corp.com" → "Acme Corp"."""
    if not domain:
        return ""
    name = domain.split(".")[0]
    return " ".join(w.capitalize() for w in name.replace("-", " ").replace("_", " ").split())


def _build_email(
    campaign: PhishingCampaign,
    target: PhishingTarget,
    tracking_id: str,
    scenario_key: str,
) -> tuple[str, str, str, str, str | None]:
    """Return (from_addr, subject, html, text, reply_to)."""
    base = _tracking_base(campaign)
    pixel_url = f"{base}/phishing/t/{tracking_id}/px"
    click_url = f"{base}/phishing/t/{tracking_id}/c"

    tpl = _SCENARIO_TEMPLATES.get(scenario_key, _SCENARIO_TEMPLATES[_DEFAULT_SCENARIO_KEY])
    ctx = _dynamic_ctx(target, scenario_key)

    first_name = target.first_name or ""
    last_name = target.last_name or ""
    greeting = f"{first_name} {last_name}".strip() or "Madame/Monsieur"

    company = _extract_company_name(campaign.domain)
    from_name = tpl["from_name"]
    if tpl.get("internal") and company:
        from_name = f"{from_name} — {company}"

    company_suffix = f" — {company}" if company else ""
    raw_subject = tpl["subject"](ctx) if callable(tpl["subject"]) else tpl["subject"]
    subject: str = raw_subject.replace("{company_suffix}", company_suffix)

    html: str = tpl["html"](greeting, click_url, pixel_url, ctx)
    text: str = tpl["text"](greeting, click_url, ctx)

    from_email = settings.PHISHING_FROM_EMAIL or settings.RESEND_FROM
    from_addr = f"{from_name} <{from_email}>"
    reply_to: str | None = None
    if tpl.get("internal"):
        host = _lookalike_host(campaign)
        if host:
            reply_to = f"{from_name} <noreply@{host}>"
    return from_addr, subject, html, text, reply_to


def _send_phishing_email(
    to_email: str,
    from_addr: str,
    subject: str,
    html: str,
    text: str,
    reply_to: str | None = None,
) -> None:
    resend.api_key = settings.RESEND_API_KEY
    payload: dict = {
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    }
    if reply_to:
        payload["reply_to"] = reply_to
    resend.Emails.send(payload)


async def _activate_due_campaigns(db: AsyncSession) -> None:
    """Passe en 'sending' les campagnes planifiées dont l'heure d'envoi est arrivée."""
    now = datetime.now(UTC)
    due_result = await db.execute(
        select(PhishingCampaign).where(
            PhishingCampaign.status == CampaignStatus.SCHEDULED,
            PhishingCampaign.scheduled_at <= now,
        )
    )
    for due in due_result.scalars().all():
        due.status = CampaignStatus.SENDING
        due.started_at = now
        due.updated_at = now
        logger.info(f"Phishing batch: activating scheduled campaign {due.id}")
    await db.commit()


async def _finalize_campaign(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Toutes les cibles envoyées : passe la campagne en 'active' (phase résultats)
    et notifie le propriétaire par email (best-effort, n'interrompt jamais le batch)."""
    campaign.status = CampaignStatus.ACTIVE
    campaign.finished_at = datetime.now(UTC)
    campaign.updated_at = datetime.now(UTC)
    await db.flush()
    user_result = await db.execute(select(User).where(User.id == campaign.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        return
    try:
        from app.services.email_service import send_campaign_complete

        await asyncio.to_thread(
            send_campaign_complete,
            user.email,
            campaign.name,
            campaign.id,
            campaign.targets_count,
            campaign.emails_sent,
            campaign.opened_count,
            campaign.clicked_count,
            campaign.submitted_count,
        )
    except Exception as exc:
        logger.warning(
            f"Failed to send campaign complete notification (campaign_id={campaign.id}): {exc}"
        )


async def _send_campaign_batch(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Envoie un lot (batch_size) d'emails en attente d'une campagne. Si plus aucune
    cible en attente et que la campagne était en envoi, la finalise."""
    scenario_keys: list[str] = json.loads(campaign.scenario_keys or "[]")
    if not scenario_keys:
        scenario_keys = [_DEFAULT_SCENARIO_KEY]

    batch_size = campaign.batch_size or settings.PHISHING_BATCH_SIZE
    pending_result = await db.execute(
        select(PhishingTarget)
        .where(
            PhishingTarget.campaign_id == campaign.id,
            PhishingTarget.status == TargetStatus.PENDING,
        )
        .limit(batch_size)
    )
    pending = list(pending_result.scalars().all())

    if not pending:
        if campaign.status == CampaignStatus.SENDING:
            await _finalize_campaign(campaign, db)
        return

    sent_count = 0
    for target in pending:
        # Round-robin scenario assignment across targets
        scenario_key = scenario_keys[target.id % len(scenario_keys)]
        tracking_id = str(uuid.uuid4())
        from_addr, subject, html, text, reply_to = _build_email(
            campaign, target, tracking_id, scenario_key
        )
        try:
            await asyncio.to_thread(
                _send_phishing_email,
                target.email,
                from_addr,
                subject,
                html,
                text,
                reply_to,
            )
            target.tracking_id = tracking_id
            target.scenario_key = scenario_key
            target.status = TargetStatus.EMAIL_SENT
            target.email_sent_at = datetime.now(UTC)
            campaign.emails_sent += 1
            sent_count += 1
        except Exception as exc:
            logger.warning(f"Failed to send phishing email (target_id={target.id}): {exc}")

    campaign.updated_at = datetime.now(UTC)
    logger.info(f"Phishing batch: sent {sent_count} emails for campaign {campaign.id}")


async def send_pending_batch() -> None:
    """
    Called by APScheduler every 15 min and immediately on campaign launch.
    Sends up to PHISHING_BATCH_SIZE pending emails for active campaigns.
    Skips silently if another batch run is already in progress.
    """
    if _batch_lock.locked():
        return

    async with _batch_lock:
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await _activate_due_campaigns(db)

            campaigns_result = await db.execute(
                select(PhishingCampaign).where(
                    PhishingCampaign.status.in_([CampaignStatus.ACTIVE, CampaignStatus.SENDING])
                )
            )
            for campaign in campaigns_result.scalars().all():
                await _send_campaign_batch(campaign, db)

            await db.commit()


# ---------------------------------------------------------------------------
# Campaign launch
# ---------------------------------------------------------------------------


async def launch_campaign(campaign: PhishingCampaign, db: AsyncSession) -> None:
    """Transition campaign to 'sending' — actual emails sent by APScheduler batch."""
    targets_result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.campaign_id == campaign.id)
    )
    if not list(targets_result.scalars().all()):
        raise ValueError("Aucune cible uploadée pour cette campagne.")

    scenario_keys: list[str] = json.loads(campaign.scenario_keys or "[]")
    if not scenario_keys:
        raise ValueError("Aucun scénario sélectionné.")

    if not settings.RESEND_API_KEY:
        if settings.APP_ENV != "development":
            raise RuntimeError("Resend n'est pas configuré (RESEND_API_KEY manquant).")
        logger.info(
            "DEV MODE — RESEND_API_KEY absent, campagne passée en 'sending' sans envoi réel."
        )

    now = datetime.now(UTC)
    if campaign.scheduled_at and campaign.scheduled_at > now:
        campaign.status = CampaignStatus.SCHEDULED
        campaign.updated_at = now
        logger.info(f"Campaign {campaign.id} scheduled for {campaign.scheduled_at.isoformat()}")
    else:
        campaign.status = CampaignStatus.SENDING
        campaign.started_at = now
        campaign.updated_at = now
    await db.flush()


# ---------------------------------------------------------------------------
# Tracking event handlers (called from public endpoints)
# ---------------------------------------------------------------------------


async def _enroll_target_in_remediation(
    campaign: PhishingCampaign, target: PhishingTarget, db: AsyncSession
) -> None:
    """Training-on-fail : inscrit la cible piégée dans un module de remédiation
    awareness. BEST-EFFORT — ne doit JAMAIS casser le flux de tracking.

    Périmètre Lot 4 : mode consultant uniquement (l'org awareness vient du client
    RSSI) et learner DÉJÀ existant dans l'org (pas d'auto-création -> pas d'email).
    Company directe (pas d'org) et auto-création de learner = follow-up.
    """
    if not campaign.training_on_fail or campaign.rssi_client_id is None:
        return
    try:
        from app.models.awareness_learner import AwarenessLearner
        from app.models.awareness_program import AwarenessProgram
        from app.models.rssi_client import RssiClient
        from app.services.awareness_progression import enroll_learner

        client = (
            await db.execute(select(RssiClient).where(RssiClient.id == campaign.rssi_client_id))
        ).scalar_one_or_none()
        if client is None or client.awareness_organization_id is None:
            return

        learner = (
            await db.execute(
                select(AwarenessLearner).where(
                    AwarenessLearner.email == target.email,
                    AwarenessLearner.organization_id == client.awareness_organization_id,
                    AwarenessLearner.is_active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if learner is None:
            return

        # Programme de remédiation dédié si présent (slug ~ "remediation"), sinon
        # 1er programme actif en repli (ex. nis2-essentiel) pour rester fonctionnel
        # tant qu'aucun contenu de remédiation dédié n'est seedé.
        program = (
            await db.execute(
                select(AwarenessProgram)
                .where(
                    AwarenessProgram.is_active.is_(True),
                    AwarenessProgram.slug.contains("remediation"),
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if program is None:
            program = (
                await db.execute(
                    select(AwarenessProgram).where(AwarenessProgram.is_active.is_(True)).limit(1)
                )
            ).scalar_one_or_none()
        if program is None:
            return

        await enroll_learner(db, learner, program.id)
        await db.commit()
        logger.info(
            f"training-on-fail: learner {learner.id} enrolled in program {program.id} "
            f"(campaign {campaign.id}, target {target.id})"
        )
    except Exception as exc:  # best-effort : on n'interrompt jamais le tracking
        logger.warning(f"training-on-fail enrollment skipped (campaign {campaign.id}): {exc}")


async def _resolve_target_and_campaign(
    tracking_id: str, db: AsyncSession
) -> tuple[PhishingTarget | None, PhishingCampaign | None]:
    """Charge la cible (par tracking_id) ET sa campagne en UNE requête (joinedload).
    Remplace le double SELECT dupliqué dans les handlers de tracking."""
    result = await db.execute(
        select(PhishingTarget)
        .options(joinedload(PhishingTarget.campaign))
        .where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    return target, (target.campaign if target else None)


async def record_open(tracking_id: str, db: AsyncSession) -> None:
    target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    if (
        target
        and campaign
        and target.status == TargetStatus.EMAIL_SENT
        and not _is_campaign_expired(campaign)
    ):
        target.status = TargetStatus.OPENED
        target.opened_at = datetime.now(UTC)
        campaign.opened_count += 1
        campaign.updated_at = datetime.now(UTC)
        await db.commit()


async def record_click(tracking_id: str, db: AsyncSession) -> bool:
    """Record link click. Returns False if campaign has expired (endpoint should serve expiry page)."""
    target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    if target and campaign and target.status in (TargetStatus.EMAIL_SENT, TargetStatus.OPENED):
        if _is_campaign_expired(campaign):
            return False
        target.status = TargetStatus.CLICKED
        target.clicked_at = datetime.now(UTC)
        campaign.clicked_count += 1
        campaign.updated_at = datetime.now(UTC)
        await db.commit()
        if campaign.training_trigger == "click":
            await _enroll_target_in_remediation(campaign, target, db)
    return True


async def record_submit(tracking_id: str, db: AsyncSession) -> str:
    """Records submission and returns the scenario_key for the awareness page.
    Always returns a scenario_key so the awareness page is shown even after expiry."""
    target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    scenario_key = _DEFAULT_SCENARIO_KEY
    if target and campaign:
        keys = json.loads(campaign.scenario_keys or "[]")
        if target.scenario_key:
            scenario_key = target.scenario_key
        elif keys:
            scenario_key = keys[0]
        if not _is_campaign_expired(campaign) and target.status != TargetStatus.SUBMITTED:
            target.status = TargetStatus.SUBMITTED
            target.submitted_at = datetime.now(UTC)
            campaign.submitted_count += 1
            campaign.updated_at = datetime.now(UTC)
            await db.commit()
            if campaign.training_trigger == "submit":
                await _enroll_target_in_remediation(campaign, target, db)
    elif target and target.status != TargetStatus.SUBMITTED:
        target.status = TargetStatus.SUBMITTED
        await db.commit()
    return scenario_key


async def get_landing_context(tracking_id: str, db: AsyncSession) -> tuple[str, str | None, bool]:
    """Contexte pour servir la landing page : (scenario_key, landing_base, expired).
    landing_base = host de la campagne (le formulaire doit poster sur le même host)."""
    _target, campaign = await _resolve_target_and_campaign(tracking_id, db)
    if not campaign:
        return _DEFAULT_SCENARIO_KEY, None, False
    if _is_campaign_expired(campaign):
        return _DEFAULT_SCENARIO_KEY, None, True
    keys = json.loads(campaign.scenario_keys or "[]")
    scenario_key = keys[0] if keys else _DEFAULT_SCENARIO_KEY
    return scenario_key, _tracking_base(campaign), False


def _is_campaign_expired(campaign: PhishingCampaign) -> bool:
    """Return True when tracking events should no longer be recorded."""
    if campaign.status == CampaignStatus.COMPLETED:
        return True
    if campaign.started_at is not None:
        age = datetime.now(UTC) - campaign.started_at
        if age.days >= settings.PHISHING_TRACKING_TTL_DAYS:
            return True
    return False
