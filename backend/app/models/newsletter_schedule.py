from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewsletterScheduleItem(Base):
    __tablename__ = "newsletter_schedule_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)  # 1-6, display order
    actu_title: Mapped[str] = mapped_column(String(300), nullable=False)
    actu_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    actu_source: Mapped[str] = mapped_column(String(100), nullable=False)        # e.g. "BleepingComputer"
    reflex: Mapped[str] = mapped_column(String(300), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
