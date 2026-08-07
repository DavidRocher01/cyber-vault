from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Nis2Assessment(Base):
    __tablename__ = "nis2_assessments"
    # Contrainte nommee en base : la declarer ici, sinon le modele et les
    # migrations divergent (cf. test_migrations_match_models).
    #
    # POURQUOI `NULLS NOT DISTINCT`, ET POURQUOI CE N'EST PAS UN RAFFINEMENT.
    # PostgreSQL considere par defaut deux NULL comme distincts : sans cette
    # clause, `UNIQUE (user_id, client_id)` laisserait un meme compte creer une
    # infinite d'auto-evaluations personnelles, toutes avec client_id a NULL.
    # Le upsert repose sur un `scalar_one_or_none()` : il se mettrait a lever
    # des la deuxieme ligne. Disponible depuis PostgreSQL 15, la plateforme est
    # en 17. Un test le verifie en tentant l'insertion en double.
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "client_id",
            name="uq_nis2_assessments_user_client",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # Le proprietaire de l'evaluation : celui qui la remplit et la possede.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # LE SUJET de l'evaluation, et non son auteur.
    #
    # NULL  -> mon auto-evaluation. C'est le cas de l'abonne qui veut NIS2 seul,
    #          sans consultant ni RSSI fractionne : le comportement historique,
    #          inchange.
    # X     -> le dossier monte pour le client X. Un consultant en detient
    #          autant que de clients suivis, la ou le modele n'en tolerait qu'un
    #          seul par compte.
    #
    # CASCADE et non SET NULL : si la fiche client disparait, son dossier de
    # conformite n'a plus d'objet, et le repasser a NULL le confondrait avec
    # l'auto-evaluation personnelle du consultant — en y versant les reponses
    # d'un tiers.
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("rssi_clients.id", ondelete="CASCADE"), nullable=True, index=True
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
