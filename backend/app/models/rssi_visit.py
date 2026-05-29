from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RssiVisit(Base):
    __tablename__ = "rssi_visits"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("rssi_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scheduled_date: Mapped[date] = mapped_column(Date(), nullable=False, index=True)
    # monthly | quarterly | annual | urgent
    visit_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="monthly", server_default="monthly"
    )
    # onsite | remote
    location: Mapped[str] = mapped_column(
        String(20), nullable=False, default="onsite", server_default="onsite"
    )
    # planned | completed | cancelled | postponed
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="planned", server_default="planned"
    )
    notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    actual_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    duration_hours: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
