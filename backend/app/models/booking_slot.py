from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BookingSlot(Base):
    __tablename__ = "booking_slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    time: Mapped[str] = mapped_column(String(5), nullable=False)  # HH:MM
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    label: Mapped[str] = mapped_column(String(200), nullable=False, default="Appel découverte")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    bookings: Mapped[list["Booking"]] = relationship("Booking", back_populates="slot")  # type: ignore[name-defined]
