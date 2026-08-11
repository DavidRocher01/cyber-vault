import json
import re

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.limiter import limiter
from app.core.security import create_refresh_token, hash_token, make_unsubscribe_token
from app.core.ssrf import assert_no_ssrf
from app.schemas.newsletter import (
    NewsletterContentIn,
    NewsletterContentOut,
    NewsletterStatsOut,
    NewsletterSubscribeIn,
    NewsletterSubscribeOut,
    ScheduleItemIn,
    ScheduleItemOut,
    SendFromScheduleIn,
    SendIssueIn,
    SendIssueOut,
    SubscriberOut,
)
from app.services import newsletter_service

NEWSLETTER_CONTENT_KEY = "newsletter_content"

_DEFAULT_CONTENT = NewsletterContentOut(
    flash_title="Ransomware : une vague mondiale frappe les PME",
    flash_body=(
        "Cette quinzaine, plusieurs campagnes de ransomware ont ciblé des PME européennes via "
        "des emails de phishing imitant des factures. Les secteurs les plus touchés : BTP, santé "
        "et services juridiques. Coût moyen estimé : 85 000 € par incident."
    ),
    reflex_title="Activez le MFA sur tous vos comptes critiques",
    reflex_body=(
        "La double authentification bloque 99,9 % des attaques automatisées selon Microsoft. "
        "Commencez par votre messagerie professionnelle, puis votre gestionnaire de mots de passe. "
        "Outils recommandés : Bitwarden, Aegis (Android), Raivo (iOS)."
    ),
    legal_title="NIS2 : êtes-vous concerné(e) ?",
    legal_body=(
        "La directive NIS2, transposée en droit français depuis octobre 2024, élargit les "
        "obligations cyber à ~15 000 nouvelles entités (ETI, collectivités, sous-traitants). "
        "Vérifiez votre périmètre sur le site de l'ANSSI et anticipez l'audit obligatoire."
    ),
)
from app.schemas.divers import OgImageOut
from app.services.newsletter_email import (
    send_confirmation_email,
    send_newsletter_articles,
    send_newsletter_issue,
    send_newsletter_welcome,
    send_unsubscribe_confirmation,
)

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


# ── Public endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/subscribe",
    response_model=NewsletterSubscribeOut,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def subscribe(
    request: Request,
    payload: NewsletterSubscribeIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    existing = await newsletter_service.get_subscriber_by_email(db, payload.email)

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Déjà abonné(e)")
        # Not yet confirmed — resend confirmation
        if not existing.confirmed_at:
            raw_token = create_refresh_token()
            await newsletter_service.refresh_confirmation(db, existing, hash_token(raw_token))
            confirm_url = f"{settings.FRONTEND_URL}/newsletter/confirm?token={raw_token}"
            background_tasks.add_task(send_confirmation_email, existing.email, confirm_url)
            return NewsletterSubscribeOut(message="Un email de confirmation vous a été renvoyé.")
        # Was confirmed but unsubscribed — re-activate directly
        await newsletter_service.reactivate_subscriber(db, existing)
        unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={make_unsubscribe_token(existing.email)}"
        background_tasks.add_task(send_newsletter_welcome, existing.email, unsubscribe_url)
        return NewsletterSubscribeOut(message="Réabonnement confirmé !")

    raw_confirmation = create_refresh_token()
    subscriber = await newsletter_service.create_pending_subscriber(
        db,
        email=payload.email,
        confirmation_token_hash=hash_token(raw_confirmation),
        unsubscribe_token=make_unsubscribe_token(payload.email),
    )

    confirm_url = f"{settings.FRONTEND_URL}/newsletter/confirm?token={raw_confirmation}"
    background_tasks.add_task(send_confirmation_email, payload.email, confirm_url)
    logger.info(f"Newsletter subscription pending confirmation: subscriber_id={subscriber.id}")
    return NewsletterSubscribeOut(
        message="Vérifiez votre boîte mail pour confirmer votre inscription !"
    )


@router.get("/confirm")
async def confirm(
    token: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    subscriber = await newsletter_service.get_by_confirmation_token(db, hash_token(token))
    if not subscriber:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/newsletter/confirm?status=invalid",
            status_code=302,
        )
    await newsletter_service.confirm_subscriber(db, subscriber)

    unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={make_unsubscribe_token(subscriber.email)}"
    background_tasks.add_task(send_newsletter_welcome, subscriber.email, unsubscribe_url)
    logger.info(f"Newsletter confirmed: subscriber_id={subscriber.id}")
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/newsletter/confirm?status=ok",
        status_code=302,
    )


@router.get("/unsubscribe")
async def unsubscribe(
    token: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    subscriber = await newsletter_service.get_by_unsubscribe_token(db, token)
    if not subscriber:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/newsletter/unsubscribe?status=invalid",
            status_code=302,
        )
    await newsletter_service.deactivate_subscriber(db, subscriber)
    background_tasks.add_task(send_unsubscribe_confirmation, subscriber.email)
    logger.info(f"Newsletter unsubscribe: subscriber_id={subscriber.id}")
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/newsletter/unsubscribe?status=ok",
        status_code=302,
    )


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.get(
    "/admin/stats",
    response_model=NewsletterStatsOut,
    dependencies=[Depends(require_admin)],
)
async def admin_stats(db: AsyncSession = Depends(get_db)):
    total, active, pending = await newsletter_service.count_stats(db)
    return NewsletterStatsOut(
        total=total,
        active=active,
        pending_confirmation=pending,
    )


@router.get(
    "/admin/subscribers",
    response_model=list[SubscriberOut],
    dependencies=[Depends(require_admin)],
)
async def admin_subscribers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return await newsletter_service.list_subscribers(db, skip=skip, limit=limit)


@router.post(
    "/admin/send-issue",
    response_model=SendIssueOut,
    dependencies=[Depends(require_admin)],
)
async def admin_send_issue(
    payload: SendIssueIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    subscribers = await newsletter_service.list_active_subscribers(db)
    count = 0
    for sub in subscribers:
        unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={make_unsubscribe_token(sub.email)}"
        background_tasks.add_task(
            send_newsletter_issue,
            sub.email,
            unsubscribe_url,
            payload.edition,
            payload.flash_title,
            payload.flash_body,
            payload.reflex_title,
            payload.reflex_body,
            payload.legal_title,
            payload.legal_body,
        )
        count += 1
    logger.info(f"Newsletter issue #{payload.edition} queued for {count} subscribers")
    return SendIssueOut(
        sent=count, message=f"Édition #{payload.edition} envoyée à {count} abonné(s)."
    )


@router.post(
    "/admin/send-from-schedule",
    response_model=SendIssueOut,
    dependencies=[Depends(require_admin)],
)
async def admin_send_from_schedule(
    payload: SendFromScheduleIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    items = await newsletter_service.list_schedule(db)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Aucun article dans le planning.",
        )

    articles = [
        {
            "actu_title": it.actu_title,
            "actu_url": it.actu_url,
            "actu_source": it.actu_source,
            "reflex": it.reflex,
            "image_url": it.image_url,
        }
        for it in items
    ]

    subscribers = await newsletter_service.list_active_subscribers(db)
    count = 0
    for sub in subscribers:
        unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={make_unsubscribe_token(sub.email)}"
        background_tasks.add_task(
            send_newsletter_articles,
            sub.email,
            unsubscribe_url,
            payload.edition,
            articles,
        )
        count += 1

    logger.info(f"Newsletter articles issue #{payload.edition} queued for {count} subscribers")
    return SendIssueOut(
        sent=count, message=f"Édition #{payload.edition} envoyée à {count} abonné(s)."
    )


# ── OG image scraper ──────────────────────────────────────────────────────────


@router.get("/admin/og-image", dependencies=[Depends(require_admin)], response_model=OgImageOut)
async def fetch_og_image(url: str):
    """Fetch the og:image meta tag from a given URL."""
    try:
        assert_no_ssrf(url)
        async with httpx.AsyncClient(timeout=8, follow_redirects=False) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            if resp.is_redirect:
                location = resp.headers.get("location", "")
                assert_no_ssrf(location)
                async with httpx.AsyncClient(timeout=8, follow_redirects=False) as c2:
                    resp = await c2.get(location, headers={"User-Agent": "Mozilla/5.0"})
            html = resp.text
            final_url = str(resp.url)
        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            html,
            re.IGNORECASE,
        )
        if not match:
            match = re.search(
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                html,
                re.IGNORECASE,
            )
        if not match:
            return {"image_url": None}
        image_url = match.group(1).strip()
        # Résoudre les URLs relatives
        if image_url.startswith("//"):
            image_url = "https:" + image_url
        elif image_url.startswith("/"):
            from urllib.parse import urlparse

            parsed = urlparse(final_url)
            image_url = f"{parsed.scheme}://{parsed.netloc}{image_url}"
        return {"image_url": image_url}
    except Exception:  # broad: httpx errors + parsing failures
        return {"image_url": None}


# ── Schedule endpoints ─────────────────────────────────────────────────────────


@router.get("/schedule", response_model=list[ScheduleItemOut])
async def get_schedule(db: AsyncSession = Depends(get_db)):
    """Public — returns the current newsletter schedule with article links."""
    return await newsletter_service.list_schedule(db)


@router.put(
    "/admin/schedule",
    response_model=list[ScheduleItemOut],
    dependencies=[Depends(require_admin)],
)
async def update_schedule(
    items: list[ScheduleItemIn],
    db: AsyncSession = Depends(get_db),
):
    """Admin — replace the full schedule. Items must have unique positions 1-6.
    Articles must be less than 2 weeks old."""
    if len(items) == 0 or len(items) > 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="1 à 6 items requis",
        )
    positions = [i.position for i in items]
    if len(positions) != len(set(positions)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Positions dupliquées",
        )

    values = [
        {
            "position": item.position,
            "actu_title": item.actu_title,
            "actu_url": item.actu_url,
            "actu_source": item.actu_source,
            "reflex": item.reflex,
            "image_url": item.image_url,
        }
        for item in items
    ]
    created = await newsletter_service.replace_schedule(db, values)

    logger.info(f"Newsletter schedule updated — {len(created)} items")
    return created


# ── Newsletter content (editorial draft) ──────────────────────────────────────


@router.get(
    "/admin/content",
    response_model=NewsletterContentOut,
    dependencies=[Depends(require_admin)],
)
async def get_newsletter_content(db: AsyncSession = Depends(get_db)):
    """Return the current newsletter editorial draft (flash/reflex/legal)."""
    setting = await newsletter_service.get_content_setting(db, NEWSLETTER_CONTENT_KEY)
    if not setting or not setting.value_text:
        return _DEFAULT_CONTENT
    try:
        data = json.loads(setting.value_text)
        return NewsletterContentOut(**data)
    except (json.JSONDecodeError, TypeError, KeyError):
        return _DEFAULT_CONTENT


@router.put(
    "/admin/content",
    response_model=NewsletterContentOut,
    dependencies=[Depends(require_admin)],
)
async def update_newsletter_content(
    payload: NewsletterContentIn,
    db: AsyncSession = Depends(get_db),
):
    """Persist the newsletter editorial draft so the scheduler picks it up."""
    await newsletter_service.upsert_content_setting(
        db, NEWSLETTER_CONTENT_KEY, payload.model_dump_json()
    )
    logger.info("Newsletter content updated")
    return payload
