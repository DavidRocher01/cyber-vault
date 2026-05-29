from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        Index("ix_invoices_user_id_issue_date", "user_id", "issue_date"),
        Index("ix_invoices_year_seq", "invoice_year", "invoice_seq"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    invoice_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    invoice_seq: Mapped[int] = mapped_column(Integer, nullable=False)
    invoice_year: Mapped[int] = mapped_column(Integer, nullable=False)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    # subscription | audit
    type: Mapped[str] = mapped_column(String(20), nullable=False)

    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_email: Mapped[str] = mapped_column(String(255), nullable=False)
    client_address: Mapped[str | None] = mapped_column(Text, nullable=True)

    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)

    # paid | pending
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="paid")

    stripe_invoice_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship()  # type: ignore[name-defined]
