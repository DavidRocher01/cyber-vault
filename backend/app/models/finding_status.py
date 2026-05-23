from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FindingStatus(Base):
    __tablename__ = "finding_statuses"
    __table_args__ = (UniqueConstraint("site_id", "module_key", name="uq_finding_status_site_module"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id", ondelete="CASCADE"), nullable=False, index=True)
    module_key: Mapped[str] = mapped_column(String(50), nullable=False)
    # todo | in_progress | resolved | accepted_risk
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="todo")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
