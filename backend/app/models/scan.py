from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Scan(Base):
    __tablename__ = "scans"
    __table_args__ = (
        Index("ix_scans_site_id_status", "site_id", "status"),
        Index("ix_scans_site_id_finished_at", "site_id", "finished_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)

    # pending | running | done | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)
    overall_status: Mapped[str | None] = mapped_column(String(20), nullable=True)  # OK|WARNING|CRITICAL

    pdf_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON stringified
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    site: Mapped["Site"] = relationship(back_populates="scans")
