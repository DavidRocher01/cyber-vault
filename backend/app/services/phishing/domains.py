"""Verification de propriete du domaine d'expedition (DNS TXT)."""

import secrets
from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.phishing import (
    PhishingDomainVerification,
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
