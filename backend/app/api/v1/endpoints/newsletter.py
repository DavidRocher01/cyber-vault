from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_refresh_token
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.schemas.newsletter import NewsletterSubscribeIn, NewsletterSubscribeOut
from app.services.newsletter_email import send_newsletter_welcome
from app.core.config import settings

router = APIRouter(prefix="/newsletter", tags=["newsletter"])


@router.post("/subscribe", response_model=NewsletterSubscribeOut, status_code=status.HTTP_201_CREATED)
async def subscribe(
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
        # Re-subscribe
        existing.is_active = True
        existing.subscribed_at = datetime.now(timezone.utc)
        await db.flush()
        unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={existing.unsubscribe_token}"
        background_tasks.add_task(send_newsletter_welcome, existing.email, unsubscribe_url)
        return NewsletterSubscribeOut(message="Réabonnement confirmé !")

    token = create_refresh_token()
    subscriber = NewsletterSubscriber(
        email=payload.email,
        subscribed_at=datetime.now(timezone.utc),
        is_active=True,
        unsubscribe_token=token,
    )
    db.add(subscriber)
    await db.flush()

    unsubscribe_url = f"{settings.FRONTEND_URL}/newsletter/unsubscribe?token={token}"
    background_tasks.add_task(send_newsletter_welcome, payload.email, unsubscribe_url)
    logger.info(f"Newsletter subscription: {payload.email}")
    return NewsletterSubscribeOut(message="Inscription confirmée ! Vérifiez votre boîte mail.")


@router.get("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe(token: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token)
    )
    subscriber = result.scalar_one_or_none()
    if not subscriber:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lien invalide")
    subscriber.is_active = False
    await db.flush()
    logger.info(f"Newsletter unsubscribe: {subscriber.email}")
    return {"message": "Désabonnement effectué."}
