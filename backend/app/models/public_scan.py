import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PublicScan(Base):
    __tablename__ = "public_scans"
    __table_args__ = (Index("ix_public_scans_token", "session_token", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_token: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: uuid.uuid4().hex,
    )
    target_url: Mapped[str] = mapped_column(String(512), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    overall_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Gate email (lead) : le rapport complet n'est révélé qu'après saisie d'un email
    # (single opt-in). email_consent_at horodate le consentement RGPD (base légale =
    # consentement). ip_hash = sha256 salé (RGPD : pas d'IP en clair). domain sert au
    # quota « 1 rapport par email + domaine, plafond 3 domaines par email ».
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email_consent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
