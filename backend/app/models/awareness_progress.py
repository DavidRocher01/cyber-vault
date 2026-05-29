from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessProgress(Base):
    """Fine-grained module-level progress for a learner's enrollment."""

    __tablename__ = "awareness_progress"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # not_started | in_progress | completed | failed
    status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)
    # Time spent on content in seconds (heartbeat-based)
    time_spent_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Resume position for videos (seconds)
    video_resume_position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Best quiz score achieved (0-100, None if no quiz or not attempted)
    best_quiz_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    enrollment: Mapped["AwarenessEnrollment"] = relationship(back_populates="progress_records")
    module: Mapped["AwarenessModule"] = relationship(back_populates="progress_records")
