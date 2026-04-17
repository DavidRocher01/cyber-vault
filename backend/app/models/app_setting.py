from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AppSetting(Base):
    """Key/integer-value store for app-level config persisted across restarts."""
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_int: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
