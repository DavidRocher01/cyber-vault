from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Nis2Assessment(Base):
    __tablename__ = "nis2_assessments"
    # Contrainte nommee en base (migration b3c4d5e6f7a8) : la declarer ici, sinon
    # le modele et les migrations divergent (cf. test_migrations_match_models).
    __table_args__ = (UniqueConstraint("user_id", name="uq_nis2_assessments_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # One assessment per user (upsert pattern)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # JSON dict: { "item_id": "compliant" | "partial" | "non_compliant" | "na" }
    items_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    # 0-100 — recomputed on save
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
