import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.booking import Booking
from app.models.booking_slot import BookingSlot
from app.models.contact_message import ContactMessage
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


@router.get("/stats", dependencies=[Depends(_require_admin)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)
    month_str = now.strftime("%Y-%m")

    users_total = await db.scalar(select(func.count(User.id))) or 0
    active_subs = await db.scalar(
        select(func.count(Subscription.id)).where(Subscription.status == "active")
    ) or 0
    newsletter_confirmed = await db.scalar(
        select(func.count(NewsletterSubscriber.id)).where(
            NewsletterSubscriber.confirmed_at.isnot(None)
        )
    ) or 0
    bookings_month = await db.scalar(
        select(func.count(Booking.id)).where(
            Booking.status == "confirmed",
            Booking.created_at >= datetime(now.year, now.month, 1, tzinfo=timezone.utc),
        )
    ) or 0
    new_contacts = await db.scalar(
        select(func.count(ContactMessage.id)).where(ContactMessage.status == "new")
    ) or 0

    # Recent contacts (5 latest)
    recent_contacts_result = await db.execute(
        select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(5)
    )
    recent_contacts = [
        {"id": m.id, "name": m.name, "email": m.email, "need_type": m.need_type,
         "status": m.status, "created_at": m.created_at.isoformat()}
        for m in recent_contacts_result.scalars().all()
    ]

    # Recent bookings (5 latest confirmed)
    recent_bookings_result = await db.execute(
        select(Booking, BookingSlot)
        .join(BookingSlot, Booking.slot_id == BookingSlot.id)
        .where(Booking.status == "confirmed")
        .order_by(Booking.created_at.desc())
        .limit(5)
    )
    recent_bookings = [
        {"id": b.id, "name": b.name, "email": b.email,
         "date": s.date, "time": s.time, "created_at": b.created_at.isoformat()}
        for b, s in recent_bookings_result.all()
    ]

    return {
        "users_total": users_total,
        "active_subscriptions": active_subs,
        "newsletter_subscribers": newsletter_confirmed,
        "bookings_this_month": bookings_month,
        "new_contacts": new_contacts,
        "recent_contacts": recent_contacts,
        "recent_bookings": recent_bookings,
    }
