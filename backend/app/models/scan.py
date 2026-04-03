from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)

    # pending | running | done | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    overall_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # OK|WARNING|CRITICAL

    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stringified
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["Site"] = relationship(back_populates="scans")
