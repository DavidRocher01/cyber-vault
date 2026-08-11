import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.limiter import limiter
from app.models.booking_slot import BookingSlot
from app.schemas.administration import MessageOut
from app.schemas.booking import (
    BookingConfirmOut,
    BookingIn,
    BookingOut,
    SlotBatchIn,
    SlotOut,
)
from app.services import booking_service
from app.services.email_service import (
    send_booking_admin_notification,
    send_booking_confirmation,
)

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _slot_to_out(slot: BookingSlot) -> SlotOut:
    is_booked = any(b.status == "confirmed" for b in slot.bookings)
    return SlotOut(
        id=slot.id,
        date=slot.date,
        time=slot.time,
        duration_minutes=slot.duration_minutes,
        label=slot.label,
        is_booked=is_booked,
    )


def _format_date_fr(date_str: str) -> str:
    months = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]
    try:
        y, m, d = date_str.split("-")
        return f"{int(d)} {months[int(m) - 1]} {y}"
    except (ValueError, IndexError):
        return date_str


# ── Public endpoints ───────────────────────────────────────────────────────────


@router.get("/slots", response_model=list[SlotOut])
async def list_slots(month: str, db: AsyncSession = Depends(get_db)):
    """Public — returns all slots for a given month (YYYY-MM), with booking status."""
    import re

    if not re.match(r"^\d{4}-\d{2}$", month):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Format YYYY-MM requis",
        )
    slots = await booking_service.list_slots_for_month(db, month)
    return [_slot_to_out(s) for s in slots]


@router.post("", response_model=BookingConfirmOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
async def create_booking(
    request: Request,
    payload: BookingIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    slot = await booking_service.get_slot_with_bookings(db, payload.slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")

    # Check not already booked
    existing = next((b for b in slot.bookings if b.status == "confirmed"), None)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ce créneau est déjà réservé"
        )

    # Check slot is in the future
    from datetime import date as _date

    today = _date.today().isoformat()
    if slot.date < today:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Ce créneau est passé")

    cancel_token = secrets.token_urlsafe(32)
    booking = await booking_service.create_booking(
        db,
        slot_id=slot.id,
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        need_type=payload.need_type,
        message=payload.message,
        cancel_token=cancel_token,
    )

    date_label = _format_date_fr(slot.date)
    cancel_url = f"{settings.FRONTEND_URL}/reserver/annuler?token={cancel_token}"

    background_tasks.add_task(
        send_booking_confirmation,
        to_email=str(payload.email),
        name=payload.name,
        date_label=date_label,
        time_label=slot.time,
        duration_minutes=slot.duration_minutes,
        slot_label=slot.label,
        need_type=payload.need_type,
        cancel_url=cancel_url,
    )
    background_tasks.add_task(
        send_booking_admin_notification,
        admin_email=settings.CONTACT_EMAIL,
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        date_label=date_label,
        time_label=slot.time,
        need_type=payload.need_type,
        message=payload.message,
    )

    return BookingConfirmOut(
        message=f"Réservation confirmée pour le {date_label} à {slot.time}.",
        booking_id=booking.id,
    )


@router.get("/cancel", response_model=MessageOut)
async def cancel_booking(token: str, db: AsyncSession = Depends(get_db)):
    """Public — cancel a booking via the token from the confirmation email."""
    booking = await booking_service.get_booking_by_cancel_token(db, token)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    if booking.status == "cancelled":
        return {"message": "Cette réservation est déjà annulée."}
    await booking_service.cancel_booking(db, booking)
    return {"message": "Votre réservation a été annulée."}


# ── Admin endpoints ────────────────────────────────────────────────────────────


@router.post(
    "/admin/slots",
    response_model=list[SlotOut],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def add_slots(payload: SlotBatchIn, db: AsyncSession = Depends(get_db)):
    created = await booking_service.create_slots(
        db,
        [
            {
                "date": s.date,
                "time": s.time,
                "duration_minutes": s.duration_minutes,
                "label": s.label,
            }
            for s in payload.slots
        ],
    )
    return [
        SlotOut(
            id=s.id,
            date=s.date,
            time=s.time,
            duration_minutes=s.duration_minutes,
            label=s.label,
            is_booked=False,
        )
        for s in created
    ]


@router.delete(
    "/admin/slots/{slot_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_slot(slot_id: int, db: AsyncSession = Depends(get_db)):
    slot = await booking_service.get_slot(db, slot_id)
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Créneau introuvable")
    await booking_service.delete_slot(db, slot)


@router.get("/admin/slots", response_model=list[SlotOut], dependencies=[Depends(require_admin)])
async def admin_list_slots(month: str | None = None, db: AsyncSession = Depends(get_db)):
    slots = await booking_service.list_all_slots(db, month)
    return [_slot_to_out(s) for s in slots]


@router.get(
    "/admin/bookings",
    response_model=list[BookingOut],
    dependencies=[Depends(require_admin)],
)
async def admin_list_bookings(db: AsyncSession = Depends(get_db)):
    bookings = await booking_service.list_all_bookings(db)
    return [
        BookingOut(
            id=b.id,
            slot_id=b.slot_id,
            name=b.name,
            email=b.email,
            phone=b.phone,
            need_type=b.need_type,
            message=b.message,
            status=b.status,
            created_at=b.created_at.isoformat(),
        )
        for b in bookings
    ]


@router.patch(
    "/admin/bookings/{booking_id}/cancel",
    dependencies=[Depends(require_admin)],
    response_model=MessageOut,
)
async def admin_cancel_booking(booking_id: int, db: AsyncSession = Depends(get_db)):
    booking = await booking_service.get_booking(db, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Réservation introuvable")
    await booking_service.cancel_booking(db, booking)
    return {"message": "Réservation annulée."}
