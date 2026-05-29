from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AwarenessCertificate(Base):
    """
    Unforgeable attestation issued on program completion.

    The signature_hash is SHA-256 of frozen_data_json + SECRET_KEY,
    allowing public verification without exposing internal IDs.
    """

    __tablename__ = "awareness_certificates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_enrollments.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    learner_id: Mapped[int] = mapped_column(
        ForeignKey("awareness_learners.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Human-readable public ID shown on the certificate: CERT-2026-A4B7C9
    public_id: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    # Short token used in QR code URL (harder to guess than public_id)
    verification_token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    # SHA-256(frozen_data_json + SECRET_KEY) — tamper detection
    signature_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # JSON snapshot of all relevant data at time of issuance (immutable)
    frozen_data_json: Mapped[str] = mapped_column(Text, nullable=False)
    # S3 key for the generated PDF
    pdf_s3_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revocation_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # How many times the QR code verification was accessed
    verification_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    enrollment: Mapped["AwarenessEnrollment"] = relationship(back_populates="certificate")
    learner: Mapped["AwarenessLearner"] = relationship(back_populates="certificates")
