"""Audit collaboratif — invitation d'un collaborateur sur un site."""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SiteCollaborator(Base):
    __tablename__ = "site_collaborators"
    __table_args__ = (UniqueConstraint("site_id", "email", name="uq_collab_site_email"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), nullable=False, index=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # Email of the invitee (may or may not have an account)
    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Role: viewer | auditor | manager
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="viewer")

    # Status: pending | accepted | revoked
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")

    # Opaque invitation token (used in the accept link)
    invite_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)

    invited_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
