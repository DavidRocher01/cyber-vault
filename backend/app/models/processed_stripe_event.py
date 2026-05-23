from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ProcessedStripeEvent(Base):
    __tablename__ = "processed_stripe_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    stripe_event_id: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
