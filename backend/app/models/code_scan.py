from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CodeScan(Base):
    __tablename__ = "code_scans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    repo_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # pending | running | done | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # Severity counters
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="code_scans")
