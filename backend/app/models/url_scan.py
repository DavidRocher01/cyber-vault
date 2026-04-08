from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UrlScan(Base):
    __tablename__ = "url_scans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    # pending | running | done | error
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # safe | suspicious | malicious
    verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # phishing | malware | redirect | tracker
    threat_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 0-100
    threat_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    screenshot_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
