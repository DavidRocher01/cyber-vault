from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessModule(Base):
    """Individual lesson inside a program (content + optional quiz)."""

    __tablename__ = "awareness_modules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    program_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_programs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stable slug for ContentImporter (e.g. "phishing-bases")
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Order within the program
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # Content type: "video" | "markdown" | "slides" | "mixed"
    content_type: Mapped[str] = mapped_column(String(20), default="mixed", nullable=False)
    # S3 key or URL for the video (HLS manifest or MP4)
    video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # S3 key for slides PDF
    slides_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Markdown body (stored inline for short content)
    content_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_duration_minutes: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    # XP points awarded on completion
    xp_points: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    # Whether a quiz is required to complete this module
    has_quiz: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # YAML quiz definition (stored inline — loaded by ContentImporter)
    quiz_yaml: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Max quiz attempts (0 = unlimited)
    quiz_max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    # Cooldown in minutes between failed attempts
    quiz_cooldown_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    # Passing threshold (0-100)
    quiz_passing_score: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
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

    program: Mapped["AwarenessProgram"] = relationship(back_populates="modules")
    progress_records: Mapped[list["AwarenessProgress"]] = relationship(
        back_populates="module", cascade="all, delete-orphan"
    )
    quiz_attempts: Mapped[list["AwarenessQuizAttempt"]] = relationship(
        back_populates="module", cascade="all, delete-orphan"
    )
