import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.booking import Booking
from app.models.booking_slot import BookingSlot
from app.models.contact_message import ContactMessage
from app.models.invoice import Invoice
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.scan import Scan
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


def _week_label(dt: datetime) -> str:
    return dt.strftime("S%W")


@router.get("/stats", dependencies=[Depends(_require_admin)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(timezone.utc)

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

    # ── Time-series: users + scans per week (last 8 weeks) ──────────────────────
    eight_weeks_ago = now - timedelta(weeks=8)

    users_rows = await db.execute(
        select(User.created_at).where(User.created_at >= eight_weeks_ago)
    )
    scans_rows = await db.execute(
        select(Scan.created_at).where(Scan.created_at >= eight_weeks_ago)
    )

    # Build weekly buckets (Mon → Sun labels)
    week_buckets: list[dict] = []
    for i in range(7, -1, -1):
        week_start = (now - timedelta(weeks=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        iso = week_start.isocalendar()
        week_buckets.append({"label": f"S{iso[1]}", "users": 0, "scans": 0})

    def _bucket_index(dt: datetime) -> int:
        delta_weeks = int((now - dt).days / 7)
        idx = 7 - delta_weeks
        return max(0, min(7, idx))

    for (ts,) in users_rows.all():
        if ts:
            i = _bucket_index(ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc))
            week_buckets[i]["users"] += 1

    for (ts,) in scans_rows.all():
        if ts:
            i = _bucket_index(ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc))
            week_buckets[i]["scans"] += 1

    # ── Time-series: revenue per month (last 6 months) ──────────────────────────
    six_months_ago = now - timedelta(days=180)
    invoices_rows = await db.execute(
        select(Invoice.created_at, Invoice.amount_cents)
        .where(Invoice.created_at >= six_months_ago)
    )

    month_buckets: dict[str, int] = {}
    for i in range(5, -1, -1):
        ref = now - timedelta(days=30 * i)
        month_buckets[ref.strftime("%b")] = 0

    for ts, cents in invoices_rows.all():
        if ts:
            label = (ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)).strftime("%b")
            if label in month_buckets:
                month_buckets[label] = month_buckets.get(label, 0) + cents

    revenue_per_month = [{"label": k, "cents": v} for k, v in month_buckets.items()]

    return {
        "users_total": users_total,
        "active_subscriptions": active_subs,
        "newsletter_subscribers": newsletter_confirmed,
        "bookings_this_month": bookings_month,
        "new_contacts": new_contacts,
        "recent_contacts": recent_contacts,
        "recent_bookings": recent_bookings,
        "weekly_activity": week_buckets,
        "revenue_per_month": revenue_per_month,
    }
