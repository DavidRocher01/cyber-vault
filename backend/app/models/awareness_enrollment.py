from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessEnrollment(Base):
    """Enrollment of a learner in a program — tracks overall completion."""

    __tablename__ = "awareness_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    learner_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_learners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    program_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # pending | in_progress | completed | failed | expired
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    # Completion percentage (0.0 - 100.0)
    completion_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # XP earned in this enrollment
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    learner: Mapped["AwarenessLearner"] = relationship(back_populates="enrollments")
    program: Mapped["AwarenessProgram"] = relationship(back_populates="enrollments")
    organization: Mapped["AwarenessOrganization"] = relationship(back_populates="enrollments")
    progress_records: Mapped[list["AwarenessProgress"]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )
    certificate: Mapped["AwarenessCertificate | None"] = relationship(
        back_populates="enrollment", uselist=False, cascade="all, delete-orphan"
    )
