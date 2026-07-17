from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class RssiActivityLog(Base):
    __tablename__ = "rssi_consultant_activity_log"
    # Index composites présents en prod, déclarés ici pour un autogenerate vide.
    __table_args__ = (
        Index("idx_rssi_activity_client_date", "client_id", "performed_at"),
        Index("idx_rssi_activity_consultant_date", "consultant_id", "performed_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    consultant_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_id: Mapped[int] = mapped_column(
        ForeignKey("rssi_clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    performed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
