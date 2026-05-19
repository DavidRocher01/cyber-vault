from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        Index("ix_quotes_year_seq", "quote_year", "quote_seq"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    quote_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    quote_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_year: Mapped[int] = mapped_column(Integer, nullable=False)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_email: Mapped[str] = mapped_column(String(255), nullable=False)
    client_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    subject: Mapped[str] = mapped_column(String(500), nullable=False)

    # List of dicts: [{description, quantity, unit_price_cents}]
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)

    total_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)

    # sent | accepted | rejected | expired
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="sent")

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Client acceptance flow
    acceptance_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True, index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()  # type: ignore[name-defined]
