from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"), nullable=False)

    stripe_customer_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    stripe_subscription_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")

    # active | canceled | past_due | trialing
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    plan: Mapped["Plan"] = relationship(back_populates="subscriptions")
    user: Mapped["User"] = relationship()
