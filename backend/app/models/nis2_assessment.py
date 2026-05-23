from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Nis2Assessment(Base):
    __tablename__ = "nis2_assessments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # One assessment per user (upsert pattern)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # JSON dict: { "item_id": "compliant" | "partial" | "non_compliant" | "na" }
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # 0-100 — recomputed on save
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
