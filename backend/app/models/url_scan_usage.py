from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UrlScanUsage(Base):
    """Compteur monotone de consommation de scans URL (quota freemium).

    Une ligne est insérée à CHAQUE création de scan et n'est JAMAIS supprimée par la
    suppression d'un scan (droit à l'oubli). Le quota du plan Gratuit se compte sur cette
    table et non sur `url_scans` : sinon un utilisateur pourrait scanner, supprimer, puis
    rescanner à l'infini pour remettre son quota à zéro (audit 2026-07-27, finding #6).

    Aucune donnée métier (pas d'URL) : seulement l'auteur et l'horodatage, suffisants pour
    le décompte sur fenêtre glissante. La FK ondelete=CASCADE garantit que la suppression
    RGPD du compte purge bien ces lignes (seule la suppression d'un compte les efface).
    """

    __tablename__ = "url_scan_usages"
    __table_args__ = (Index("ix_url_scan_usages_user_id_created_at", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
