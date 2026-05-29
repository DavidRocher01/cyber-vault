from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessProgram(Base):
    """A training program (parcours) — ordered collection of modules."""

    __tablename__ = "awareness_programs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Stable slug used by ContentImporter (e.g. "nis2-essentiel")
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="fr", nullable=False)
    # Estimated total duration in minutes
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Passing threshold (0-100) for the program certificate
    passing_score: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    # Certificate validity in months (0 = no expiry)
    certificate_validity_months: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(20), default="1.0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    modules: Mapped[list["AwarenessModule"]] = relationship(
        back_populates="program",
        order_by="AwarenessModule.position",
        cascade="all, delete-orphan",
    )
    enrollments: Mapped[list["AwarenessEnrollment"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
