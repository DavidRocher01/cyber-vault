from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_id_status", "user_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)

    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # active | canceled | past_due | trialing
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active", index=True)

    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    user: Mapped["User"] = relationship()
