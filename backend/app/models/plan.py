from sqlalchemy import Boolean, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False
    )  # free / starter / pro / business
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price_eur: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # centimes (0, 4900, 14900, 39000)
    max_sites: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # -1 = illimité (cf. UNLIMITED_SITES)
    scan_interval_days: Mapped[int] = mapped_column(Integer, nullable=False)  # 30 (Gratuit) ou 1
    tier_level: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # 1=Gratuit 2=Starter 3=Pro 4=Business
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Export des rapports de conformité (NIS2 / ISO 27001) : réservé aux plans payants.
    # Le Gratuit peut faire l'auto-évaluation mais pas exporter le PDF (gate monétisation).
    allow_conformity_export: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")
