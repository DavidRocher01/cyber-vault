from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessLearnerBadge(Base):
    """Badge earned by a specific learner."""

    __tablename__ = "awareness_learner_badges"
    __table_args__ = (UniqueConstraint("learner_id", "badge_id", name="uq_learner_badge"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    learner_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_learners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    badge_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_badges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    learner: Mapped["AwarenessLearner"] = relationship(back_populates="earned_badges")
    badge: Mapped["AwarenessBadge"] = relationship(back_populates="earners")
