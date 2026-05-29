from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessOrganization(Base):
    """Client company enrolled in the awareness platform."""

    __tablename__ = "awareness_organizations"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Link to the CyberScan user (org admin or RSSI consultant owner)
    owner_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    siret: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Max learner seats allowed by their subscription tier
    max_learners: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    learners: Mapped[list["AwarenessLearner"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
    enrollments: Mapped[list["AwarenessEnrollment"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
