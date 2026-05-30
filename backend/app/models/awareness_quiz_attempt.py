from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessQuizAttempt(Base):
    """One quiz attempt by a learner on a module."""

    __tablename__ = "awareness_quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    learner_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_learners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    module_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_modules.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # Score achieved (0-100)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # passed | failed
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    # Duration of the attempt in seconds
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # JSON: list of {question_id, chosen_answers, is_correct, points_earned}
    answers_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Anti-cheat: log IP and user agent
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    learner: Mapped["AwarenessLearner"] = relationship(back_populates="quiz_attempts")
    module: Mapped["AwarenessModule"] = relationship(back_populates="quiz_attempts")
