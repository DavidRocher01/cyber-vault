from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from app.core.limiter import limiter
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_refresh_token
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.newsletter_schedule import NewsletterScheduleItem
from app.schemas.newsletter import (
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
from app.services.newsletter_email import (
    send_confirmation_email,
    send_newsletter_articles,
    send_newsletter_issue,
    send_newsletter_welcome,
    send_unsubscribe_confirmation,
)

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


# ── Guard admin ────────────────────────────────────────────────────────────────

def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


# ── Public endpoints ───────────────────────────────────────────────────────────

@router.post("/subscribe", response_model=NewsletterSubscribeOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def subscribe(
    request: Request,
    payload: NewsletterSubscribeIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.email == payload.email)
    )
    existing = result.scalar_one_or_none()

    if existing:
        if existing.is_active:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Déjà abonné(e)")
        # Not yet confirmed — resend confirmation
        if not existing.confirmed_at:
            token = create_refresh_token()
            existing.confirmation_token = token
            existing.subscribed_at = datetime.now(timezone.utc)
            await db.flush()
            confirm_url = f"{settings.FRONTEND_URL}/cyberscan/newsletter/confirm?token={token}"
            background_tasks.add_task(send_confirmation_email, existing.email, confirm_url)
            return NewsletterSubscribeOut(message="Un email de confirmation vous a été renvoyé.")
        # Was confirmed but unsubscribed — re-activate directly
        existing.is_active = True
        existing.subscribed_at = datetime.now(timezone.utc)
        await db.flush()
        unsubscribe_url = f"{settings.FRONTEND_URL}/cyberscan/newsletter/unsubscribe?token={existing.unsubscribe_token}"
        background_tasks.add_task(send_newsletter_welcome, existing.email, unsubscribe_url)
        return NewsletterSubscribeOut(message="Réabonnement confirmé !")

    confirmation_token = create_refresh_token()
    unsubscribe_token = create_refresh_token()
    subscriber = NewsletterSubscriber(
        email=payload.email,
        subscribed_at=datetime.now(timezone.utc),
        is_active=False,
        confirmation_token=confirmation_token,
        unsubscribe_token=unsubscribe_token,
    )
    db.add(subscriber)
    await db.flush()

    confirm_url = f"{settings.FRONTEND_URL}/cyberscan/newsletter/confirm?token={confirmation_token}"
    background_tasks.add_task(send_confirmation_email, payload.email, confirm_url)
    logger.info(f"Newsletter subscription pending confirmation: subscriber_id={subscriber.id}")
    return NewsletterSubscribeOut(message="Vérifiez votre boîte mail pour confirmer votre inscription !")


@router.get("/confirm")
async def confirm(
    token: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.confirmation_token == token)
    )
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/cyberscan/newsletter/confirm?status=invalid",
            status_code=302,
        )
    subscriber.is_active = True
    subscriber.confirmed_at = datetime.now(timezone.utc)
    subscriber.confirmation_token = None
    await db.flush()

    unsubscribe_url = f"{settings.FRONTEND_URL}/cyberscan/newsletter/unsubscribe?token={subscriber.unsubscribe_token}"
    background_tasks.add_task(send_newsletter_welcome, subscriber.email, unsubscribe_url)
    logger.info(f"Newsletter confirmed: subscriber_id={subscriber.id}")
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/cyberscan/newsletter/confirm?status=ok",
        status_code=302,
    )


@router.get("/unsubscribe")
async def unsubscribe(
    token: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token)
    )
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/cyberscan/newsletter/unsubscribe?status=invalid",
            status_code=302,
        )
    subscriber.is_active = False
    await db.flush()
    background_tasks.add_task(send_unsubscribe_confirmation, subscriber.email)
    logger.info(f"Newsletter unsubscribe: subscriber_id={subscriber.id}")
    return RedirectResponse(
        url=f"{settings.FRONTEND_URL}/cyberscan/newsletter/unsubscribe?status=ok",
        status_code=302,
    )


# ── Admin endpoints ────────────────────────────────────────────────────────────

@router.get("/admin/stats", response_model=NewsletterStatsOut, dependencies=[Depends(_require_admin)])
async def admin_stats(db: AsyncSession = Depends(get_db)):
    total_r = await db.execute(select(func.count()).select_from(NewsletterSubscriber))
    active_r = await db.execute(
        select(func.count()).select_from(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)  # noqa: E712
    )
    pending_r = await db.execute(
        select(func.count()).select_from(NewsletterSubscriber).where(
            NewsletterSubscriber.is_active == False,  # noqa: E712
            NewsletterSubscriber.confirmation_token != None,  # noqa: E711
        )
    )
    return NewsletterStatsOut(
        total=total_r.scalar_one(),
        active=active_r.scalar_one(),
        pending_confirmation=pending_r.scalar_one(),
    )


@router.get("/admin/subscribers", response_model=list[SubscriberOut], dependencies=[Depends(_require_admin)])
async def admin_subscribers(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsletterSubscriber).order_by(NewsletterSubscriber.subscribed_at.desc())
    )
    return result.scalars().all()


@router.post("/admin/send-issue", response_model=SendIssueOut, dependencies=[Depends(_require_admin)])
async def admin_send_issue(
    payload: SendIssueIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)  # noqa: E712
    )
    subscribers = result.scalars().all()
    count = 0
    for sub in subscribers:
        unsubscribe_url = f"{settings.FRONTEND_URL}/cyberscan/newsletter/unsubscribe?token={sub.unsubscribe_token}"
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
    return SendIssueOut(sent=count, message=f"Édition #{payload.edition} envoyée à {count} abonné(s).")


@router.post("/admin/send-from-schedule", response_model=SendIssueOut, dependencies=[Depends(_require_admin)])
async def admin_send_from_schedule(
    payload: SendFromScheduleIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    schedule_result = await db.execute(
        select(NewsletterScheduleItem).order_by(NewsletterScheduleItem.position)
    )
    items = schedule_result.scalars().all()
    if not items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Aucun article dans le planning.")

    articles = [
        {"actu_title": it.actu_title, "actu_url": it.actu_url, "actu_source": it.actu_source, "reflex": it.reflex}
        for it in items
    ]

    subscribers_result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.is_active == True)  # noqa: E712
    )
    subscribers = subscribers_result.scalars().all()
    count = 0
    for sub in subscribers:
        unsubscribe_url = f"{settings.FRONTEND_URL}/cyberscan/newsletter/unsubscribe?token={sub.unsubscribe_token}"
        background_tasks.add_task(send_newsletter_articles, sub.email, unsubscribe_url, payload.edition, articles)
        count += 1

    logger.info(f"Newsletter articles issue #{payload.edition} queued for {count} subscribers")
    return SendIssueOut(sent=count, message=f"Édition #{payload.edition} envoyée à {count} abonné(s).")


# ── Schedule endpoints ─────────────────────────────────────────────────────────

@router.get("/schedule", response_model=list[ScheduleItemOut])
async def get_schedule(db: AsyncSession = Depends(get_db)):
    """Public — returns the current newsletter schedule with article links."""
    result = await db.execute(
        select(NewsletterScheduleItem).order_by(NewsletterScheduleItem.position)
    )
    return result.scalars().all()


@router.put("/admin/schedule", response_model=list[ScheduleItemOut], dependencies=[Depends(_require_admin)])
async def update_schedule(
    items: list[ScheduleItemIn],
    db: AsyncSession = Depends(get_db),
):
    """Admin — replace the full schedule. Items must have unique positions 1-6.
    Articles must be less than 2 weeks old."""
    if len(items) == 0 or len(items) > 6:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="1 à 6 items requis")
    positions = [i.position for i in items]
    if len(positions) != len(set(positions)):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Positions dupliquées")

    now = datetime.now(timezone.utc)

    # Delete existing
    existing = await db.execute(select(NewsletterScheduleItem))
    for row in existing.scalars().all():
        await db.delete(row)
    await db.flush()

    # Insert new
    created = []
    for item in sorted(items, key=lambda x: x.position):
        row = NewsletterScheduleItem(
            position=item.position,
            actu_title=item.actu_title,
            actu_url=item.actu_url,
            actu_source=item.actu_source,
            reflex=item.reflex,
            updated_at=now,
        )
        db.add(row)
        created.append(row)
    await db.flush()

    logger.info(f"Newsletter schedule updated — {len(created)} items")
    return created
