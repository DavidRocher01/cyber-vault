from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SourceAcquisition(Base):
    """D'où vient une conversion — enregistré AU MOMENT où elle se produit.

    Ce modèle n'existe que pour répondre à une question : quelle source
    d'acquisition produit des clients payants (cf. `docs/ANALYTICS.md`).

    **Aucun identifiant de visiteur.** Pas de cookie, pas de `localStorage`, pas
    d'empreinte de navigateur, et aucun suivi de page en page. On ne relie pas
    une navigation à une personne : on qualifie une conversion qui a déjà eu
    lieu, parce que quelqu'un a volontairement rempli un formulaire.

    C'est ce qui permet de se passer de bandeau de consentement, et c'est une
    contrainte, pas une préférence — un vendeur de conformité NIS2 ne demande pas
    à ses visiteurs l'autorisation de les pister. Ne pas ajouter ici de colonne
    qui identifierait un visiteur avant sa conversion.
    """

    __tablename__ = "sources_acquisition"
    __table_args__ = (
        # Les trois lectures de l'onglet Acquisition : par source, par étape, par
        # page d'atterrissage — toutes bornées dans le temps.
        Index("ix_sources_acq_date_evenement", "cree_le", "evenement"),
        Index("ix_sources_acq_source", "utm_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Étape franchie : scan_gratuit | email_debloque | inscription | abonnement.
    # Volontairement une chaîne courte et non un enum SQL : ajouter une étape ne
    # doit pas coûter une migration de type sur une table de mesure.
    evenement: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Fournis par le client, donc NORMALISÉS avant écriture (cf.
    # `acquisition_service.normaliser`) : minuscules, jeu de caractères restreint,
    # longueur bornée. Sans quoi un endpoint public devient un stockage gratuit.
    utm_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(64), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # DOMAINE seul, jamais l'URL complète : une URL référente peut porter un
    # identifiant de session ou un terme de recherche, donc de la donnée
    # personnelle dont on n'a aucun usage.
    referent_domaine: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Route interne d'entrée (« /scan-gratuit »), sans query string.
    page_atterrissage: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Rattachements. `user_id` est posé à l'inscription : c'est lui qui permet de
    # joindre une source au revenu, via `subscriptions`. ON DELETE SET NULL —
    # l'effacement d'un compte (RGPD art. 17) ne doit pas faire disparaître la
    # statistique, seulement son rattachement.
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    public_scan_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("public_scans.id", ondelete="SET NULL"), nullable=True
    )

    # Montant mensuel en centimes, renseigné seulement sur `abonnement`. Figé à
    # l'instant de la conversion : si la grille change ensuite, l'historique
    # d'acquisition ne doit pas être réécrit rétroactivement.
    montant_mensuel_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    cree_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
