"""Registre des fichiers déposés sur la plateforme.

POURQUOI UNE TABLE, ET NON UNE COLONNE SUR `RssiDeliverable`.

Le point de dépôt renvoie une clé de stockage **avant** qu'un livrable existe :
le client téléverse, reçoit une clé, puis crée le livrable qui la référence. Un
fichier peut donc être stocké sans jamais être rattaché — et l'est déjà
aujourd'hui, dès qu'un dépôt est abandonné en cours de route. Une colonne sur le
livrable ne verrait pas ces fichiers-là.

Trois besoins de `docs/DEPOT_DOCUMENTS.md` convergent vers le même objet :

- l'**état d'analyse** est une propriété du fichier, pas du livrable ;
- la **rétention** (étape 4) ne peut pas effacer ce dont elle n'a pas trace ;
- le **quota par client** suppose de pouvoir sommer les tailles déposées.

C'est donc le fichier lui-même qu'on enregistre, et le livrable le référence.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.enums import StatutAnalyse


class FichierDepose(Base):
    __tablename__ = "fichiers_deposes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # Clé de stockage renvoyée par `storage.upload_file` — S3 en production,
    # chemin relatif en développement. Unique : c'est par elle qu'on retrouve un
    # fichier depuis un livrable, qui n'en connaît rien d'autre.
    cle_stockage: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)

    nom_original: Mapped[str] = mapped_column(String(255), nullable=False)
    taille_octets: Mapped[int] = mapped_column(Integer, nullable=False)
    type_mime: Mapped[str] = mapped_column(String(120), nullable=False)

    # `SET NULL` ET NON `CASCADE` SUR LES DEUX — corrigé le 2026-08-04.
    #
    # La première version cascadait. L'intention était RGPD : le compte parti,
    # ses dépôts n'ont plus de titulaire. L'effet obtenu était l'inverse. La
    # cascade efface la LIGNE ; elle ne touche pas à l'objet sur S3, que seul du
    # code applicatif sait supprimer. Un client supprimé laissait donc le fichier
    # stocké **et** effaçait la seule trace permettant de le retrouver — soit
    # exactement ce que ce registre existe pour empêcher, réintroduit par
    # l'autre bout.
    #
    # Avec `SET NULL`, la ligne survit, perd son rattachement, et devient un
    # orphelin au sens de `purger_orphelins` : objet effacé PUIS ligne, avec
    # réessai si le stockage résiste. Le fichier disparaît réellement sous
    # `DELAI_ORPHELIN_JOURS`, au lieu de rester indéfiniment sans titulaire.
    #
    # `depose_par_id` est donc nullable : perdre le déposant n'empêche pas de
    # purger, et le conserver après suppression du compte serait précisément la
    # donnée sans base légale qu'on voulait éviter.
    depose_par_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # Client RSSI concerné, quand le dépôt s'inscrit dans un suivi.
    client_id: Mapped[int | None] = mapped_column(
        ForeignKey("rssi_clients.id", ondelete="SET NULL"), nullable=True, index=True
    )

    statut_analyse: Mapped[str] = mapped_column(
        String(20), nullable=False, default=StatutAnalyse.EN_ANALYSE, index=True
    )
    # Renseigné au verdict. Nul tant que l'analyse n'a pas répondu.
    analyse_le: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    depose_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,  # la purge de rétention balaiera par date
    )
