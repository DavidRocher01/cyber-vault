from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RssiClient(Base):
    __tablename__ = "rssi_clients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    consultant_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Formula / commercial
    formula: Mapped[str | None] = mapped_column(String(20), nullable=True)   # essentiel|premium|excellence
    monthly_amount: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    contract_start_date: Mapped[date | None] = mapped_column(Date(), nullable=True)
    contract_renewal_at: Mapped[date | None] = mapped_column(Date(), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", server_default="active")

    # Integrations
    notion_workspace_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    pipedrive_deal_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pennylane_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    extra_data: Mapped[str | None] = mapped_column(Text(), nullable=True)  # JSON

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
