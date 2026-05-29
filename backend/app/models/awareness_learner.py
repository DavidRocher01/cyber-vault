from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessLearner(Base):
    """Employee of a client organisation — authenticates via magic link."""

    __tablename__ = "awareness_learners"
    __table_args__ = (Index("ix_awareness_learners_org_active", "organization_id", "is_active"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(5), default="fr", nullable=False)
    # Magic-link token (hashed) — short-lived, refreshed on each login request
    access_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # GDPR: anonymise on departure, but certificates kept 5 years
    anonymized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    organization: Mapped["AwarenessOrganization"] = relationship(back_populates="learners")
    enrollments: Mapped[list["AwarenessEnrollment"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[list["AwarenessQuizAttempt"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    certificates: Mapped[list["AwarenessCertificate"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
    earned_badges: Mapped[list["AwarenessLearnerBadge"]] = relationship(
        back_populates="learner", cascade="all, delete-orphan"
    )
