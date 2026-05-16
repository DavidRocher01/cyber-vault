from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSetting(Base):
    """Key/value store for app-level config persisted across restarts."""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_int: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
