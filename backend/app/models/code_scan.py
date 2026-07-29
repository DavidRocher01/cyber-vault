from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class CodeScan(Base):
    __tablename__ = "code_scans"
    __table_args__ = (
        Index("ix_code_scans_user_id_status", "user_id", "status"),
        Index("ix_code_scans_user_id_created_at", "user_id", "created_at"),
        # Index unique PARTIEL (migration f7a8b9c0d1e2) : un seul scan actif par
        # utilisateur. Le predicat fait partie de la definition — sans lui le
        # modele decrirait un unique global, bien plus restrictif que la realite.
        Index(
            "uq_code_scan_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    repo_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    repo_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # pending | running | done | failed
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending", index=True)

    # Severity counters
    critical_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    results_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="code_scans")
