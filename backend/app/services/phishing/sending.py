"""Moteur d'envoi : construction des e-mails, lots, activation."""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from email.utils import parseaddr

import resend
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import CampaignStatus, TargetStatus
from app.models.phishing import (
    PhishingCampaign,
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

_batch_lock = asyncio.Lock()
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


def _adresse_expediteur() -> str:
    """Adresse NUE de l'expéditeur des simulations, sans nom d'affichage.

    L'appelant compose ensuite `Nom <adresse>` : lui rendre autre chose qu'une
    adresse nue produit un en-tête invalide.

    C'est exactement ce qui arrivait jusqu'au 2026-08-03. Le code faisait
    `PHISHING_FROM_EMAIL or RESEND_FROM`, or les deux réglages n'ont pas le même
    format : le premier est une adresse nue, le second une adresse RFC 5322
    complète avec nom d'affichage. Aucun des deux n'étant injecté dans la tâche
    ECS, le repli s'appliquait et produisait des chevrons imbriqués —

        Support Microsoft 365 <Rocher Cybersécurité <no-reply@exemple.com>>

    que `email.utils.parseaddr` réduit à un nom vide ET une adresse vide. Les
    simulations ne pouvaient pas partir.

    Les tests ne l'ont pas vu parce qu'ils vérifiaient tous des morceaux du nom
    d'affichage (`"Acme" in from_addr`), jamais la validité de l'adresse.

    `parseaddr` accepte les deux formes et rend toujours l'adresse seule : le
    repli redevient sûr quel que soit le format de `RESEND_FROM`.
    """
    brute = settings.PHISHING_FROM_EMAIL or settings.RESEND_FROM
    return parseaddr(brute)[1] or brute


class DomaineExpeditionInvalideError(RuntimeError):
    """Le domaine d'expédition des simulations n'est pas séparé du transactionnel."""


def _domaine(adresse: str) -> str:
    return adresse.rsplit("@", 1)[-1].strip().lower()


def verifier_domaine_expedition() -> None:
    """Refuse d'envoyer des simulations depuis le domaine transactionnel.

    POURQUOI CETTE GARDE EXISTE. Le but d'une bonne simulation est que les
    salariés SIGNALENT le message. Ces signalements remontent à Microsoft et
    Google et pèsent sur la réputation du domaine expéditeur. L'envoyer depuis
    celui qui porte les réinitialisations de mot de passe et les factures revient
    donc à leur nuire délibérément — et d'autant plus que la simulation réussit.

    ELLE NE CONNAÎT AUCUN NOM DE DOMAINE. Elle compare l'expéditeur des
    simulations à l'expéditeur transactionnel : elle continue donc de protéger
    après n'importe quel changement de domaine, sans être modifiée.

    Le repli silencieux qu'elle remplace était le vrai danger : `PHISHING_FROM_
    EMAIL or RESEND_FROM` fait qu'une valeur absente, vide ou mal saisie renvoie
    au domaine principal SANS que rien ne le signale. C'est exactement le
    scénario d'une migration de domaine bâclée. Mieux vaut refuser bruyamment
    que délivrer discrètement.
    """
    simulation = _domaine(_adresse_expediteur())
    transactionnel = _domaine(parseaddr(settings.RESEND_FROM)[1] or settings.RESEND_FROM)
    if not simulation or simulation == transactionnel:
        raise DomaineExpeditionInvalideError(
            "Les simulations partiraient du domaine transactionnel "
            f"({transactionnel or 'indéterminé'}). Renseignez PHISHING_FROM_EMAIL "
            "avec une adresse sur un domaine distinct, vérifié chez Resend."
        )


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

    from_addr = f"{from_name} <{_adresse_expediteur()}>"
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
    # Seconde barrière, sur le chemin d'envoi lui-même. Le contrôle au
    # lancement ne couvre pas les campagnes lancées AVANT l'existence de cette
    # garde, ni un changement de configuration survenu depuis : le planificateur
    # reprend une campagne déjà `sending` sans repasser par l'endpoint.
    verifier_domaine_expedition()
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
