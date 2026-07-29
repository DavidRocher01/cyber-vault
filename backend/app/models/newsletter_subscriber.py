from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    # L'index et la contrainte d'unicite de confirmation_token portent des noms
    # explicites (crees par la migration c1d2e3f4a5b6) : les declarer ici plutot
    # que via index=/unique= sur la colonne, sinon SQLAlchemy en deduit
    # ix_newsletter_subscribers_confirmation_token et le schema diverge des
    # migrations (cf. test_migrations_match_models).
    __table_args__ = (
        UniqueConstraint("confirmation_token", name="uq_newsletter_confirmation_token"),
        Index("ix_newsletter_confirmation_token", "confirmation_token"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    subscribed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # 64 = longueur d'un HMAC-SHA256 en hexa. Les colonnes ont ete retaillees
    # 512 -> 64 par la migration j4k5l6m7n8o9 ; le modele etait reste a 512.
    confirmation_token: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unsubscribe_token: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
