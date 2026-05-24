from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DarkwebDossier(Base):
    """B2B dark web exposure dossier for a company domain."""
    __tablename__ = "darkweb_dossiers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), nullable=False)
    # pending | processing | completed | failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_emails: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    exposed_emails: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_breach_instances: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unverified_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    monitor_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_monitored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_monitor_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    targets: Mapped[list["DarkwebDossierTarget"]] = relationship(
        "DarkwebDossierTarget", back_populates="dossier", lazy="selectin"
    )


class DarkwebDossierTarget(Base):
    """Individual email result within a dossier."""
    __tablename__ = "darkweb_dossier_targets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    dossier_id: Mapped[int] = mapped_column(
        ForeignKey("darkweb_dossiers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # clean | exposed | error | pending
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # verified_clean | exposed | api_error | rate_limited | pending
    check_status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    total_breaches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    breach_sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dossier: Mapped["DarkwebDossier"] = relationship("DarkwebDossier", back_populates="targets")
