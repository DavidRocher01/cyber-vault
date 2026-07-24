"""Service d'acces aux reservations et creneaux (bookings/slots)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.booking import Booking
from app.models.booking_slot import BookingSlot


async def list_slots_for_month(db: AsyncSession, month: str) -> list[BookingSlot]:
    """Creneaux d'un mois (YYYY-MM) avec leurs reservations prechargees."""
    result = await db.execute(
        select(BookingSlot)
        .where(BookingSlot.date.like(f"{month}-%"))
        .order_by(BookingSlot.date, BookingSlot.time)
        .options(selectinload(BookingSlot.bookings))
    )
    return list(result.scalars().unique().all())


async def get_slot_with_bookings(db: AsyncSession, slot_id: int) -> BookingSlot | None:
    """Creneau par id avec ses reservations prechargees, sinon None."""
    result = await db.execute(
        select(BookingSlot)
        .where(BookingSlot.id == slot_id)
        .options(selectinload(BookingSlot.bookings))
    )
    return result.scalars().unique().one_or_none()


async def create_booking(
    db: AsyncSession,
    *,
    slot_id: int,
    name: str,
    email: str,
    phone: str | None,
    need_type: str,
    message: str | None,
    cancel_token: str,
) -> Booking:
    """Cree une reservation confirmee sur un creneau."""
    booking = Booking(
        slot_id=slot_id,
        name=name,
        email=email,
        phone=phone,
        need_type=need_type,
        message=message,
        status="confirmed",
        cancel_token=cancel_token,
        created_at=datetime.now(UTC),
    )
    db.add(booking)
    await db.commit()
    return booking


async def get_booking_by_cancel_token(db: AsyncSession, token: str) -> Booking | None:
    """Reservation par son token d'annulation, sinon None."""
    result = await db.execute(select(Booking).where(Booking.cancel_token == token))
    return result.scalar_one_or_none()


async def get_booking(db: AsyncSession, booking_id: int) -> Booking | None:
    """Reservation par id, sinon None."""
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    return result.scalar_one_or_none()


async def cancel_booking(db: AsyncSession, booking: Booking) -> None:
    """Passe une reservation au statut annule."""
    booking.status = "cancelled"
    await db.commit()


async def create_slots(db: AsyncSession, slots: list[dict]) -> list[BookingSlot]:
    """Cree un lot de creneaux a partir de dicts (date/time/duration_minutes/label)."""
    now = datetime.now(UTC)
    created: list[BookingSlot] = []
    for s in slots:
        slot = BookingSlot(
            date=s["date"],
            time=s["time"],
            duration_minutes=s["duration_minutes"],
            label=s["label"],
            created_at=now,
        )
        db.add(slot)
        created.append(slot)
    await db.commit()
    return created


async def get_slot(db: AsyncSession, slot_id: int) -> BookingSlot | None:
    """Creneau par id, sinon None."""
    result = await db.execute(select(BookingSlot).where(BookingSlot.id == slot_id))
    return result.scalars().unique().one_or_none()


async def delete_slot(db: AsyncSession, slot: BookingSlot) -> None:
    """Supprime un creneau."""
    await db.delete(slot)
    await db.commit()


async def list_all_slots(db: AsyncSession, month: str | None = None) -> list[BookingSlot]:
    """Tous les creneaux (option filtre par mois) avec reservations prechargees."""
    q = (
        select(BookingSlot)
        .order_by(BookingSlot.date, BookingSlot.time)
        .options(selectinload(BookingSlot.bookings))
    )
    if month:
        q = q.where(BookingSlot.date.like(f"{month}-%"))
    result = await db.execute(q)
    return list(result.scalars().unique().all())


async def list_all_bookings(db: AsyncSession) -> list[Booking]:
    """Toutes les reservations, les plus recentes d'abord."""
    result = await db.execute(select(Booking).order_by(Booking.created_at.desc()))
    return list(result.scalars().all())
