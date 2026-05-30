from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.booking import Booking
from app.models.booking_slot import BookingSlot
from app.models.contact_message import ContactMessage
from app.models.invoice import Invoice
from app.models.newsletter_subscriber import NewsletterSubscriber
from app.models.scan import Scan
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


def _week_label(dt: datetime) -> str:
    return dt.strftime("S%W")


@router.get("/stats", dependencies=[Depends(require_admin)])
async def get_stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(UTC)

    users_total = await db.scalar(select(func.count(User.id))) or 0
    active_subs = (
        await db.scalar(select(func.count(Subscription.id)).where(Subscription.status == "active"))
        or 0
    )
    newsletter_confirmed = (
        await db.scalar(
            select(func.count(NewsletterSubscriber.id)).where(
                NewsletterSubscriber.confirmed_at.isnot(None)
            )
        )
        or 0
    )
    bookings_month = (
        await db.scalar(
            select(func.count(Booking.id)).where(
                Booking.status == "confirmed",
                Booking.created_at >= datetime(now.year, now.month, 1, tzinfo=UTC),
            )
        )
        or 0
    )
    new_contacts = (
        await db.scalar(select(func.count(ContactMessage.id)).where(ContactMessage.status == "new"))
        or 0
    )

    # Recent contacts (5 latest)
    recent_contacts_result = await db.execute(
        select(ContactMessage).order_by(ContactMessage.created_at.desc()).limit(5)
    )
    recent_contacts = [
        {
            "id": m.id,
            "name": m.name,
            "email": m.email,
            "need_type": m.need_type,
            "status": m.status,
            "created_at": m.created_at.isoformat(),
        }
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
        {
            "id": b.id,
            "name": b.name,
            "email": b.email,
            "date": s.date,
            "time": s.time,
            "created_at": b.created_at.isoformat(),
        }
        for b, s in recent_bookings_result.all()
    ]

    # ── Time-series: users + scans per week (last 8 weeks) ──────────────────────
    eight_weeks_ago = now - timedelta(weeks=8)

    users_rows = await db.execute(select(User.created_at).where(User.created_at >= eight_weeks_ago))
    scans_rows = await db.execute(select(Scan.created_at).where(Scan.created_at >= eight_weeks_ago))

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
            i = _bucket_index(ts if ts.tzinfo else ts.replace(tzinfo=UTC))
            week_buckets[i]["users"] += 1

    for (ts,) in scans_rows.all():
        if ts:
            i = _bucket_index(ts if ts.tzinfo else ts.replace(tzinfo=UTC))
            week_buckets[i]["scans"] += 1

    # ── Time-series: revenue per month (last 6 months) ──────────────────────────
    six_months_ago = now - timedelta(days=180)
    invoices_rows = await db.execute(
        select(Invoice.created_at, Invoice.amount_cents).where(Invoice.created_at >= six_months_ago)
    )

    # Build 6 distinct month buckets by decrementing calendar months (no timedelta ambiguity)
    month_order: list[str] = []
    month_buckets: dict[str, int] = {}
    for i in range(5, -1, -1):
        month = now.month - i
        year = now.year
        while month <= 0:
            month += 12
            year -= 1
        key = f"{year}-{month:02d}"
        month_order.append(key)
        month_buckets[key] = 0

    for ts, cents in invoices_rows.all():
        if ts:
            key = (ts if ts.tzinfo else ts.replace(tzinfo=UTC)).strftime("%Y-%m")
            if key in month_buckets:
                month_buckets[key] += cents

    revenue_per_month = [
        {"label": datetime.strptime(k, "%Y-%m").strftime("%b"), "cents": month_buckets[k]}
        for k in month_order
    ]

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


@router.post("/awareness/sync-content", dependencies=[Depends(require_admin)])
async def sync_awareness_content():
    """Reimporte le contenu NIS2 depuis les fichiers YAML/Markdown (idempotent)."""
    from app.core.database import AsyncSessionLocal
    from app.services.awareness_content_importer import import_from_directory

    content_dir = Path(__file__).parents[4] / "content" / "fr"
    if not content_dir.exists():
        return {"error": f"Dossier contenu introuvable : {content_dir}"}

    async with AsyncSessionLocal() as db:
        try:
            summary = await import_from_directory(db, content_dir)
            logger.info(
                f"Admin sync: {summary['programs']} programmes, {summary['modules']} modules"
            )
            return {
                "status": "ok",
                "programs": summary["programs"],
                "modules": summary["modules"],
                "errors": summary.get("errors", []),
            }
        except Exception as exc:
            logger.error(f"Admin sync failed: {exc}")
            return {"error": str(exc)}
