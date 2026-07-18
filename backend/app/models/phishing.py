from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PhishingCampaign(Base):
    __tablename__ = "phishing_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Propriétaire = le compte qui lance la campagne (consultant OU entreprise).
    # L'ownership (get/patch/launch) se fait TOUJOURS sur user_id.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Attribution : campagne rattachée à un client RSSI (mode consultant) ou NULL
    # (mode entreprise directe). Ne sert PAS au contrôle d'accès, seulement à
    # l'affichage sur la fiche client + à l'org awareness du client (training-on-fail).
    rssi_client_id: Mapped[int | None] = mapped_column(
        ForeignKey("rssi_clients.id", ondelete="CASCADE"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Valeurs = CampaignStatus (models/enums.py) :
    # draft | pending_verification | ready | scheduled | sending | active | completed | cancelled
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    # express | standard | premium | quarterly | monthly
    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False, default="standard")

    # Domain ownership verification (the company's real domain)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    domain_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Look-alike domain used in phishing email links (separate from target domain)
    # e.g. "monentreprise-rh.com" or None → falls back to PHISHING_BASE_URL
    lookalike_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Scenarios: JSON array of scenario IDs, e.g. '["ceo-fraud","o365-credentials"]'
    scenario_keys: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Training-on-fail : inscrire automatiquement la cible piégée dans un module de
    # remédiation awareness (mode consultant : org awareness du client). training_trigger
    # = quand déclencher : "click" (au clic) ou "submit" (à la soumission d'identifiants).
    training_on_fail: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    training_trigger: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="click"
    )

    # Cadence : nombre d'emails envoyés par tick de scheduler (toutes les 15 min).
    # NULL = repli sur le global settings.PHISHING_BATCH_SIZE.
    batch_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Stats
    targets_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    emails_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    opened_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicked_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    submitted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Consent & scheduling
    cgu_accepted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    targets: Mapped[list["PhishingTarget"]] = relationship(
        back_populates="campaign", cascade="all, delete-orphan"
    )


class PhishingTarget(Base):
    __tablename__ = "phishing_targets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("phishing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # UUID used in tracking URLs — assigned when email is sent
    tracking_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, unique=True, index=True
    )

    # Scenario sent to this target — assigned at send time
    scenario_key: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # pending | email_sent | opened | clicked | submitted
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # Per-event timestamps
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    campaign: Mapped["PhishingCampaign"] = relationship(back_populates="targets")


class PhishingDomainVerification(Base):
    __tablename__ = "phishing_domain_verifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    domain: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # DNS TXT token: add TXT record "_rocher-verify.<domain>" with this value
    verification_token: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
