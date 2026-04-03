from sqlalchemy import Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)   # starter / pro / business
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_eur: Mapped[int] = mapped_column(Integer, nullable=False)              # centimes (900, 2900, 7900)
    max_sites: Mapped[int] = mapped_column(Integer, nullable=False)
    scan_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)     # 30 ou 7
    tier_level: Mapped[int] = mapped_column(Integer, nullable=False)             # 2, 3, 4
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")
