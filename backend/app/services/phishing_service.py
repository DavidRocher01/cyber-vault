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

from app.core.config import settings
from app.models.phishing import (
    PhishingCampaign,
    PhishingDomainVerification,
    PhishingTarget,
)
from app.models.user import User
from app.services.phishing_templates import (
    _DEFAULT_SCENARIO_KEY,
    _LANDING_MICROSOFT,
    _LANDING_TEMPLATES,
    _PIXEL_GIF,
    _SCENARIO_AWARENESS,
    _SCENARIO_LANDING,
    _SCENARIO_TEMPLATES,
    _dynamic_ctx,
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
        status="draft",
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
    campaign.status = "cancelled"
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


def _tracking_base(campaign: PhishingCampaign) -> str:
    """Determine the base URL for tracking links (look-alike or default)."""
    if campaign.lookalike_domain:
        domain = campaign.lookalike_domain.rstrip("/")
        if not domain.startswith("http"):
            domain = f"https://{domain}"
        return domain
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
    if campaign.lookalike_domain and tpl.get("internal"):
        raw = campaign.lookalike_domain
        if raw.startswith("https://"):
            raw = raw[8:]
        elif raw.startswith("http://"):
            raw = raw[7:]
        raw = raw.rstrip("/")
        reply_to = f"{from_name} <noreply@{raw}>"
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
            # Activate any scheduled campaigns whose send time has arrived
            now = datetime.now(UTC)
            due_result = await db.execute(
                select(PhishingCampaign).where(
                    PhishingCampaign.status == "scheduled",
                    PhishingCampaign.scheduled_at <= now,
                )
            )
            for due in due_result.scalars().all():
                due.status = "sending"
                due.started_at = now
                due.updated_at = now
                logger.info(f"Phishing batch: activating scheduled campaign {due.id}")
            await db.commit()

            campaigns_result = await db.execute(
                select(PhishingCampaign).where(PhishingCampaign.status.in_(["active", "sending"]))
            )
            campaigns = list(campaigns_result.scalars().all())

            for campaign in campaigns:
                scenario_keys: list[str] = json.loads(campaign.scenario_keys or "[]")
                if not scenario_keys:
                    scenario_keys = [_DEFAULT_SCENARIO_KEY]

                batch_size = campaign.batch_size or settings.PHISHING_BATCH_SIZE
                pending_result = await db.execute(
                    select(PhishingTarget)
                    .where(
                        PhishingTarget.campaign_id == campaign.id,
                        PhishingTarget.status == "pending",
                    )
                    .limit(batch_size)
                )
                pending = list(pending_result.scalars().all())

                if not pending:
                    # All emails sent — move to 'active' results phase
                    if campaign.status == "sending":
                        campaign.status = "active"
                        campaign.finished_at = datetime.now(UTC)
                        campaign.updated_at = datetime.now(UTC)
                        await db.flush()
                        # Notify campaign owner
                        user_result = await db.execute(
                            select(User).where(User.id == campaign.user_id)
                        )
                        user = user_result.scalar_one_or_none()
                        if user:
                            try:
                                from app.services.email_service import (
                                    send_campaign_complete,
                                )

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
                    continue

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
                        target.status = "email_sent"
                        target.email_sent_at = datetime.now(UTC)
                        campaign.emails_sent += 1
                        sent_count += 1
                    except Exception as exc:
                        logger.warning(
                            f"Failed to send phishing email (target_id={target.id}): {exc}"
                        )

                campaign.updated_at = datetime.now(UTC)
                logger.info(f"Phishing batch: sent {sent_count} emails for campaign {campaign.id}")

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
        campaign.status = "scheduled"
        campaign.updated_at = now
        logger.info(f"Campaign {campaign.id} scheduled for {campaign.scheduled_at.isoformat()}")
    else:
        campaign.status = "sending"
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


async def record_open(tracking_id: str, db: AsyncSession) -> None:
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    if target and target.status == "email_sent":
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign and not _is_campaign_expired(campaign):
            target.status = "opened"
            target.opened_at = datetime.now(UTC)
            campaign.opened_count += 1
            campaign.updated_at = datetime.now(UTC)
            await db.commit()


async def record_click(tracking_id: str, db: AsyncSession) -> bool:
    """Record link click. Returns False if campaign has expired (endpoint should serve expiry page)."""
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    if target and target.status in ("email_sent", "opened"):
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            if _is_campaign_expired(campaign):
                return False
            target.status = "clicked"
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
    result = await db.execute(
        select(PhishingTarget).where(PhishingTarget.tracking_id == tracking_id)
    )
    target = result.scalar_one_or_none()
    scenario_key = _DEFAULT_SCENARIO_KEY
    if target:
        campaign_result = await db.execute(
            select(PhishingCampaign).where(PhishingCampaign.id == target.campaign_id)
        )
        campaign = campaign_result.scalar_one_or_none()
        if campaign:
            keys = json.loads(campaign.scenario_keys or "[]")
            if target.scenario_key:
                scenario_key = target.scenario_key
            elif keys:
                scenario_key = keys[0]
            if not _is_campaign_expired(campaign) and target.status != "submitted":
                target.status = "submitted"
                target.submitted_at = datetime.now(UTC)
                campaign.submitted_count += 1
                campaign.updated_at = datetime.now(UTC)
                await db.commit()
                if campaign.training_trigger == "submit":
                    await _enroll_target_in_remediation(campaign, target, db)
        elif target.status != "submitted":
            target.status = "submitted"
            await db.commit()
    return scenario_key


def _is_campaign_expired(campaign: PhishingCampaign) -> bool:
    """Return True when tracking events should no longer be recorded."""
    if campaign.status == "completed":
        return True
    if campaign.started_at is not None:
        age = datetime.now(UTC) - campaign.started_at
        if age.days >= settings.PHISHING_TRACKING_TTL_DAYS:
            return True
    return False


def get_pixel_gif() -> bytes:
    return _PIXEL_GIF


def get_landing_html(
    tracking_id: str, scenario_key: str = _DEFAULT_SCENARIO_KEY, base: str | None = None
) -> str:
    # La landing doit poster sur le MÊME host que celui qui l'a servie (le domaine
    # look-alike si la campagne en a un, sinon PHISHING_BASE_URL) — sinon un
    # formulaire servi depuis le look-alike posterait vers un autre host.
    base = (base or settings.PHISHING_BASE_URL).rstrip("/")
    action = f"{base}/phishing/t/{tracking_id}/s"
    template_name = _SCENARIO_LANDING.get(scenario_key, "microsoft")
    html = _LANDING_TEMPLATES.get(template_name, _LANDING_MICROSOFT)
    return html.replace("ACTION_URL", action)


_AWARENESS_TPL = '<!DOCTYPE html>\n<html lang="fr">\n<head>\n<meta charset="UTF-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n<title>Exercice de cybersécurité — Rocher Cybersécurité</title>\n<style>\n*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}\nbody{\n  background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);\n  min-height:100vh;display:flex;flex-direction:column;\n  align-items:center;justify-content:center;\n  font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Arial,sans-serif;\n  padding:24px;\n}\n.top-banner{\n  width:100%;max-width:640px;\n  background:rgba(239,68,68,0.12);border:1px solid rgba(239,68,68,0.35);\n  border-radius:10px 10px 0 0;padding:10px 20px;\n  display:flex;align-items:center;gap:10px;\n}\n.top-banner svg{flex-shrink:0}\n.top-banner span{font-size:13px;font-weight:600;color:#fca5a5;letter-spacing:.3px}\n.card{\n  background:#1e293b;border:1px solid #334155;border-top:none;\n  border-radius:0 0 16px 16px;max-width:640px;width:100%;overflow:hidden;\n}\n.hero{\n  background:linear-gradient(180deg,#0f172a 0%,#1e293b 100%);\n  padding:40px 40px 32px;text-align:center;border-bottom:1px solid #334155;\n}\n.scenario-chip{\n  display:inline-flex;align-items:center;gap:6px;\n  background:rgba(37,99,235,0.15);border:1px solid rgba(59,130,246,0.4);\n  color:#93c5fd;font-size:12px;font-weight:600;padding:5px 14px;\n  border-radius:999px;margin-bottom:20px;letter-spacing:.4px;text-transform:uppercase;\n}\n.emoji-wrap{\n  font-size:64px;line-height:1;margin-bottom:20px;\n  filter:drop-shadow(0 0 24px rgba(245,158,11,0.3));\n}\nh1{font-size:26px;font-weight:800;color:#f1f5f9;margin-bottom:10px;line-height:1.2}\nh1 span{color:#f59e0b}\n.subtitle{font-size:15px;color:#94a3b8;line-height:1.6;max-width:480px;margin:0 auto}\n.no-data-badge{\n  display:inline-flex;align-items:center;gap:6px;\n  background:rgba(16,185,129,0.12);border:1px solid rgba(16,185,129,0.3);\n  color:#6ee7b7;font-size:12px;font-weight:600;padding:5px 14px;\n  border-radius:999px;margin-top:18px;\n}\n.body{padding:32px 40px}\n.section-title{\n  font-size:11px;font-weight:700;color:#64748b;letter-spacing:1.2px;\n  text-transform:uppercase;margin-bottom:16px;\n  display:flex;align-items:center;gap:8px;\n}\n.section-title::after{content:\'\';flex:1;height:1px;border-top:1px solid #334155}\n.flags-list{display:flex;flex-direction:column;gap:12px}\n.flag-row{\n  display:flex;align-items:flex-start;gap:14px;background:#0f172a;\n  border:1px solid #334155;border-left:3px solid #f59e0b;\n  border-radius:8px;padding:14px 16px;\n}\n.flag-icon{flex-shrink:0;margin-top:2px}\n.flag-text{font-size:14px;color:#cbd5e1;line-height:1.55}\n.tip-box{\n  margin-top:24px;background:rgba(14,116,144,0.1);\n  border:1px solid rgba(14,116,144,0.3);border-radius:10px;\n  padding:18px 20px;display:flex;gap:14px;align-items:flex-start;\n}\n.tip-box svg{flex-shrink:0;margin-top:2px}\n.tip-box p{font-size:13px;color:#a5f3fc;line-height:1.6}\n.tip-box strong{color:#22d3ee}\n.footer{\n  border-top:1px solid #334155;padding:18px 40px;\n  display:flex;align-items:center;justify-content:space-between;\n}\n.logo{display:flex;align-items:center;gap:8px}\n.logo-icon{\n  width:28px;height:28px;\n  background:linear-gradient(135deg,#2563eb,#7c3aed);\n  border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:14px;\n}\n.logo-text{font-size:13px;font-weight:700;color:#94a3b8}\n.footer-right{font-size:12px;color:#475569}\n</style>\n</head>\n<body>\n\n<div class="top-banner">\n  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">\n    <circle cx="12" cy="12" r="10"/>\n    <line x1="12" y1="8" x2="12" y2="12"/>\n    <line x1="12" y1="16" x2="12.01" y2="16"/>\n  </svg>\n  <span>ALERTE — Vous venez de cliquer sur un lien de simulation de phishing</span>\n</div>\n\n<div class="card">\n  <div class="hero">\n    <div class="scenario-chip">\n      <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>\n      Scénario : __LABEL__\n    </div>\n    <div class="emoji-wrap">__ICON__</div>\n    <h1>Vous êtes tombé(e) dans le piège<br>\n      <span>d&rsquo;__LABEL__ __ACCORD__</span>\n    </h1>\n    <p class="subtitle">\n      Cet email faisait partie d&rsquo;un exercice de sensibilisation organisé\n      par votre entreprise en partenariat avec\n      <strong style="color:#e2e8f0">Rocher Cybersécurité</strong>.\n    </p>\n    <div class="no-data-badge">\n      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">\n        <polyline points="20 6 9 17 4 12"/>\n      </svg>\n      Aucune donnée réelle capturée ni stockée\n    </div>\n  </div>\n\n  <div class="body">\n    <p class="section-title">Signaux d&rsquo;alerte que vous auriez pu repérer</p>\n    <div class="flags-list">\n      __FLAGS__\n    </div>\n\n    <div class="tip-box">\n      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#22d3ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\n        <circle cx="12" cy="12" r="10"/>\n        <line x1="12" y1="16" x2="12" y2="12"/>\n        <line x1="12" y1="8" x2="12.01" y2="8"/>\n      </svg>\n      <p>En cas de doute sur un email réel, <strong>ne cliquez jamais</strong> sur les liens\n      &mdash; contactez directement votre équipe IT ou signalez l&rsquo;email via le bouton\n      &laquo;&nbsp;Signaler un phishing&nbsp;&raquo; de votre messagerie.</p>\n    </div>\n  </div>\n\n  <div class="footer">\n    <div class="logo">\n      <div class="logo-icon">🛡️</div>\n      <span class="logo-text">Rocher Cybersécurité</span>\n    </div>\n    <span class="footer-right">Simulation de phishing — Exercice interne</span>\n  </div>\n</div>\n\n</body>\n</html>'

_FLAG_ROW_TPL = '<div class="flag-row"><div class="flag-icon"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div><p class="flag-text">__TEXT__</p></div>'

_EXPIRED_HTML = (
    '<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">'
    '<meta name="viewport" content="width=device-width,initial-scale=1">'
    "<title>Exercice terminé — Rocher Cybersécurité</title>"
    "<style>*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
    "body{background:linear-gradient(135deg,#0f172a 0%,#1e1b4b 100%);"
    "min-height:100vh;display:flex;align-items:center;justify-content:center;"
    "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;padding:24px}"
    ".card{background:#1e293b;border:1px solid #334155;border-radius:16px;"
    "padding:48px 40px;max-width:440px;width:100%;text-align:center}"
    ".icon{font-size:48px;margin-bottom:20px}"
    "h1{font-size:20px;font-weight:700;color:#f1f5f9;margin:0 0 12px}"
    "p{font-size:14px;color:#94a3b8;line-height:1.6;margin:0}"
    ".badge{display:inline-flex;align-items:center;gap:6px;"
    "background:rgba(14,116,144,.15);color:#67e8f9;"
    "font-size:12px;font-weight:600;padding:5px 14px;border-radius:999px;margin-top:24px}"
    "</style></head><body>"
    '<div class="card">'
    '<div class="icon">\U0001f6e1️</div>'
    "<h1>Cet exercice de phishing a expiré</h1>"
    "<p>Le lien que vous avez suivi faisait partie d'une simulation de phishing. "
    "L'exercice est maintenant terminé — aucune donnée n'a été transmise.</p>"
    '<div class="badge">Rocher Cybersécurité — Simulation termin\xe9e</div>'
    "</div></body></html>"
)


def get_expired_html() -> str:
    return _EXPIRED_HTML


def get_awareness_html(scenario_key: str = _DEFAULT_SCENARIO_KEY) -> str:
    _fallback = {
        "label": "un email de phishing",
        "icon": "\u26a0\ufe0f",
        "red_flags": [
            "L\u2019exp\xe9diteur n\u2019\xe9tait pas celui qu\u2019il pr\xe9tendait \xeatre",
            "Le lien ne pointait pas vers le domaine officiel attendu",
            "Une urgence artificielle vous poussait \xe0 agir sans r\xe9fl\xe9chir",
        ],
    }
    sc = _SCENARIO_AWARENESS.get(scenario_key, _fallback)
    label = sc["label"]
    icon = sc["icon"]
    flags = sc["red_flags"]
    accord = "simul\xe9e" if label.startswith("une ") else "simul\xe9"

    flag_rows = "".join(_FLAG_ROW_TPL.replace("__TEXT__", f) for f in flags)
    return (
        _AWARENESS_TPL.replace("__LABEL__", label)
        .replace("__ACCORD__", accord)
        .replace("__ICON__", icon)
        .replace("__FLAGS__", flag_rows)
    )
