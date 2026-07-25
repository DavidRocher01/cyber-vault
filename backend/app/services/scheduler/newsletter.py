"""Job newsletter Radar Cyber — envoyé toutes les 2 semaines aux abonnés actifs."""

import asyncio
import json

from loguru import logger
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.utils import mask_email
from app.models.app_setting import AppSetting
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.services.newsletter_email import send_newsletter_issue

_NEWSLETTER_EDITION_KEY = "newsletter_edition"
_NEWSLETTER_CONTENT_KEY = "newsletter_content"

_DEFAULT_NEWSLETTER_CONTENT = {
    "flash_title": "Ransomware : une vague mondiale frappe les PME",
    "flash_body": (
        "Cette quinzaine, plusieurs campagnes de ransomware ont ciblé des PME européennes via "
        "des emails de phishing imitant des factures. Les secteurs les plus touchés : BTP, santé "
        "et services juridiques. Coût moyen estimé : 85 000 € par incident."
    ),
    "reflex_title": "Activez le MFA sur tous vos comptes critiques",
    "reflex_body": (
        "La double authentification bloque 99,9 % des attaques automatisées selon Microsoft. "
        "Commencez par votre messagerie professionnelle, puis votre gestionnaire de mots de passe. "
        "Outils recommandés : Bitwarden, Aegis (Android), Raivo (iOS)."
    ),
    "legal_title": "NIS2 : êtes-vous concerné(e) ?",
    "legal_body": (
        "La directive NIS2, transposée en droit français depuis octobre 2024, élargit les "
        "obligations cyber à ~15 000 nouvelles entités (ETI, collectivités, sous-traitants). "
        "Vérifiez votre périmètre sur le site de l'ANSSI et anticipez l'audit obligatoire."
    ),
}


async def _send_biweekly_newsletter() -> None:
    """Send the Radar Cyber newsletter to all active subscribers."""
    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        # Read and atomically increment the persisted edition counter
        setting = await db.get(AppSetting, _NEWSLETTER_EDITION_KEY)
        if setting is None:
            setting = AppSetting(key=_NEWSLETTER_EDITION_KEY, value_int=1)
            db.add(setting)
            await db.flush()
        edition = setting.value_int
        setting.value_int = edition + 1

        # Read editorial content from DB; fall back to defaults if not set
        content_setting = await db.get(AppSetting, _NEWSLETTER_CONTENT_KEY)
        content = _DEFAULT_NEWSLETTER_CONTENT
        if content_setting and content_setting.value_text:
            try:
                content = json.loads(content_setting.value_text)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Contenu newsletter en base illisible (JSON), fallback defaut : {}", exc
                )

        result = await db.execute(
            select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)
        )
        subscribers = result.scalars().all()
        await db.commit()

    flash_title = content["flash_title"]
    flash_body = content["flash_body"]
    reflex_title = content["reflex_title"]
    reflex_body = content["reflex_body"]
    legal_title = content["legal_title"]
    legal_body = content["legal_body"]

    for sub in subscribers:
        unsubscribe_url = (
            f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={sub.unsubscribe_token}"
        )
        try:
            await asyncio.to_thread(
                send_newsletter_issue,
                to_email=sub.email,
                unsubscribe_url=unsubscribe_url,
                edition=edition,
                flash_title=flash_title,
                flash_body=flash_body,
                reflex_title=reflex_title,
                reflex_body=reflex_body,
                legal_title=legal_title,
                legal_body=legal_body,
            )
        except Exception as exc:
            logger.warning(f"Newsletter send failed for {mask_email(sub.email)}: {exc}")

    logger.info(f"Newsletter édition #{edition} envoyée à {len(subscribers)} abonné(s)")
