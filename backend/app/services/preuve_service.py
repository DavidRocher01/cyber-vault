"""Rattachement de pieces justificatives aux criteres NIS2 — etape 5c.

Une conformite sans preuve est une declaration ; avec preuves, c'est un dossier
opposable. Ce service tient le lien, la couche HTTP ne fait que l'appeler.

CE QU'IL NE FAIT PAS. Il ne repond pas a la place de l'utilisateur. Une piece
DOCUMENTE une declaration, elle ne la remplit pas : c'est la meme regle que
`awareness_nis2_report.preuve_formation`, et pour la meme raison — une
auto-evaluation remplie automatiquement n'est plus une declaration et perd sa
valeur devant un auditeur.
"""

from __future__ import annotations

from datetime import datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fichier_depose import FichierDepose
from app.models.preuve_critere import PreuveCritere
from app.services.nis2_catalogue import ALL_ITEM_IDS


class CritereInconnuError(ValueError):
    """L'identifiant de critere ne figure pas au catalogue NIS2."""

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Critère inconnu : {item_id!r}.")


def valider_critere(item_id: str) -> str:
    """Verifie que le critere existe au catalogue, et renvoie sa forme propre.

    POURQUOI CE CONTROLE EST INDISPENSABLE. `item_id` n'a pas de cle etrangere :
    le catalogue est du code, pas une table. Sans validation, une piece rattachee
    a un identifiant errone serait acceptee, stockee, comptee dans le quota — et
    n'apparaitrait jamais nulle part. Elle echapperait aussi a la purge des
    orphelins, puisqu'elle sert formellement de preuve. Un fichier invisible et
    imperissable : exactement ce que le registre existe pour empecher.
    """
    propre = item_id.strip()
    if propre not in ALL_ITEM_IDS:
        raise CritereInconnuError(item_id)
    return propre


async def rattacher(
    db: AsyncSession,
    *,
    assessment_id: int,
    item_id: str,
    fichier_id: int,
    now: datetime,
) -> PreuveCritere:
    """Rattache un fichier deja au registre a un critere de l'evaluation.

    Idempotent : rattacher deux fois la meme piece au meme critere renvoie le
    lien existant plutot que de lever. Un double-clic ne doit pas produire une
    erreur que l'utilisateur ne saurait pas interpreter.
    """
    critere = valider_critere(item_id)

    existant = (
        await db.execute(
            select(PreuveCritere).where(
                PreuveCritere.nis2_assessment_id == assessment_id,
                PreuveCritere.item_id == critere,
                PreuveCritere.fichier_id == fichier_id,
            )
        )
    ).scalar_one_or_none()
    if existant is not None:
        return existant

    preuve = PreuveCritere(
        nis2_assessment_id=assessment_id,
        item_id=critere,
        fichier_id=fichier_id,
        rattache_le=now,
    )
    db.add(preuve)
    await db.commit()
    await db.refresh(preuve)
    logger.info("Preuve rattachée au critère {} (évaluation {})", critere, assessment_id)
    return preuve


async def detacher(db: AsyncSession, *, assessment_id: int, preuve_id: int) -> bool:
    """Retire un rattachement. Renvoie False s'il n'existait pas.

    LE FICHIER N'EST PAS EFFACE ICI. Detacher, c'est dire « cette piece ne
    justifie pas ce critere », pas « supprimez ce document ». Le fichier redevient
    simplement non reference : la purge des orphelins s'en chargera si plus rien
    ne le designe, avec son delai de grace habituel.

    `assessment_id` fait partie du filtre et non de la seule verification : sans
    lui, connaitre un identifiant de preuve suffirait a detacher une piece du
    dossier d'un autre.
    """
    preuve = (
        await db.execute(
            select(PreuveCritere).where(
                PreuveCritere.id == preuve_id,
                PreuveCritere.nis2_assessment_id == assessment_id,
            )
        )
    ).scalar_one_or_none()
    if preuve is None:
        return False

    await db.delete(preuve)
    await db.commit()
    return True


async def cle_de_la_piece(db: AsyncSession, *, assessment_id: int, preuve_id: int) -> str | None:
    """Cle de stockage d'une piece, si elle appartient bien a cette evaluation.

    `assessment_id` fait partie du filtre et non d'une verification faite
    ensuite : sans lui, connaitre un identifiant de piece suffirait a obtenir un
    lien de telechargement sur le document d'un autre.
    """
    return (
        await db.execute(
            select(FichierDepose.cle_stockage)
            .join(PreuveCritere, PreuveCritere.fichier_id == FichierDepose.id)
            .where(
                PreuveCritere.id == preuve_id,
                PreuveCritere.nis2_assessment_id == assessment_id,
            )
        )
    ).scalar_one_or_none()


async def preuves_par_critere(db: AsyncSession, assessment_id: int) -> dict[str, list[dict]]:
    """Les pieces d'une evaluation, regroupees par critere.

    L'etat d'analyse antivirus est renvoye tel quel : c'est lui qui decide si la
    piece est telechargeable, et l'interface doit pouvoir le montrer plutot que
    de proposer un lien qui echouera.
    """
    lignes = (
        await db.execute(
            select(PreuveCritere, FichierDepose)
            .join(FichierDepose, FichierDepose.id == PreuveCritere.fichier_id)
            .where(PreuveCritere.nis2_assessment_id == assessment_id)
            .order_by(PreuveCritere.rattache_le)
        )
    ).all()

    par_critere: dict[str, list[dict]] = {}
    for preuve, fichier in lignes:
        par_critere.setdefault(preuve.item_id, []).append(
            {
                "id": preuve.id,
                "nom": fichier.nom_original,
                "taille_octets": fichier.taille_octets,
                "cle_stockage": fichier.cle_stockage,
                "statut_analyse": fichier.statut_analyse,
                "rattache_le": preuve.rattache_le,
            }
        )
    return par_critere
