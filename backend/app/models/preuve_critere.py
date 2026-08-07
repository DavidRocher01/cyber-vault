"""Une piece justificative rattachee a un critere de conformite — etape 5c.

CE QUE CETTE TABLE CHANGE. Une conformite sans preuve est une declaration ; avec
preuves, c'est un dossier opposable. C'est la raison d'etre de toute l'etape 5.

POURQUOI UNE TABLE DE LIAISON, ET PAS UN CHAMP DANS `items_json`. Ce dernier est
une colonne `Text` contenant `{item_id: statut}`. Y loger des pieces jointes
reviendrait a stocker des references de fichiers dans du JSON libre, sans cle
etrangere : rien n'empecherait de pointer un fichier efface, et la purge n'aurait
aucun moyen de savoir qu'un fichier sert de preuve.

POURQUOI ELLE POINTE `FichierDepose` ET NON `RssiDeliverable`. Le livrable est
propre au RSSI ; le registre des fichiers, lui, est commun aux deux parcours.
C'est ce choix qui permet a l'abonne qui veut NIS2 seul — ni consultant, ni
client d'un RSSI fractionne — de rattacher ses propres pieces. En prime, la
regle de delivrance s'applique sans une ligne de plus : une preuve en cours
d'analyse antivirus n'est pas telechargeable.

ISO 27001 VIENDRA S'Y AJOUTER. `nis2_assessment_id` est non nul aujourd'hui.
Quand ISO recevra le meme traitement, la migration le rendra nullable, ajoutera
`iso_assessment_id` et une contrainte exigeant qu'exactement un des deux soit
renseigne. La couche de regles — purge, quota, retention — reste alors unique,
ce qu'une seconde table separee aurait interdit.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PreuveCritere(Base):
    __tablename__ = "preuves_criteres"
    # Le meme fichier ne sert qu'une fois pour un meme critere. Rien n'interdit
    # en revanche qu'il en serve plusieurs : une politique de securite peut
    # justifier a la fois la gouvernance et la revue annuelle.
    __table_args__ = (
        UniqueConstraint(
            "nis2_assessment_id",
            "item_id",
            "fichier_id",
            name="uq_preuves_criteres_evaluation_critere_fichier",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # CASCADE : une preuve n'a aucun sens sans l'evaluation qu'elle documente.
    nis2_assessment_id: Mapped[int] = mapped_column(
        ForeignKey("nis2_assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # L'identifiant du critere dans `app/services/nis2_catalogue.py` (ex. "rssi").
    # Pas de cle etrangere possible : le catalogue est du code, pas une table.
    # C'est donc la couche service qui le valide contre `ALL_ITEM_IDS` — un
    # identifiant inconnu rendrait la preuve invisible sans jamais lever.
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # CASCADE : si la ligne de registre disparait, le lien ne pointe plus rien.
    # Le cas devrait rester theorique — les fichiers rattaches sont justement
    # exclus des deux purges, precisement parce qu'ils servent de preuve.
    fichier_id: Mapped[int] = mapped_column(
        ForeignKey("fichiers_deposes.id", ondelete="CASCADE"), nullable=False, index=True
    )

    rattache_le: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), index=True
    )
