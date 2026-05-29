from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessBadge(Base):
    """Badge definition (shared catalog — not per-org)."""

    __tablename__ = "awareness_badges"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Stable slug used in code: "first_step", "perfectionist", "streak_7" …
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Emoji or icon name used in the UI
    icon: Mapped[str] = mapped_column(String(50), default="🏅", nullable=False)
    # XP bonus awarded when the badge is earned
    xp_bonus: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Category: "engagement" | "performance" | "streak" | "social" | "special"
    category: Mapped[str] = mapped_column(String(30), default="engagement", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    earners: Mapped[list["AwarenessLearnerBadge"]] = relationship(
        back_populates="badge", cascade="all, delete-orphan"
    )
