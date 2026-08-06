"""Registre des fichiers déposés et verdict de l'analyse antivirus.

Ce service détient une seule règle, et c'est elle qui compte :
**un fichier n'est délivré que s'il est réputé sain.**

Le reste — l'enregistrement du dépôt, la réception du verdict — n'existe que
pour la rendre applicable. Cf. `docs/DEPOT_DOCUMENTS.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.enums import StatutAnalyse
from app.models.fichier_depose import FichierDepose


def statut_a_l_enregistrement() -> StatutAnalyse:
    """État donné à un dépôt qui vient d'être stocké.

    Sans analyse en service, marquer `en_analyse` bloquerait tout sans rien
    protéger : personne ne rendrait jamais son verdict. On enregistre donc
    `sain`, ce qui laisse le registre se remplir — la rétention et le quota en
    dépendent — sans introduire une porte fermée qu'aucune clé n'ouvre.
    """
    if settings.ANTIVIRUS_DEPOT_ACTIF:
        return StatutAnalyse.EN_ANALYSE
    return StatutAnalyse.SAIN


async def enregistrer_depot(
    db: AsyncSession,
    *,
    cle_stockage: str,
    nom_original: str,
    taille_octets: int,
    type_mime: str,
    depose_par_id: int,
    client_id: int | None = None,
) -> FichierDepose:
    """Inscrit un fichier tout juste stocké dans le registre."""
    fichier = FichierDepose(
        cle_stockage=cle_stockage,
        nom_original=nom_original,
        taille_octets=taille_octets,
        type_mime=type_mime,
        depose_par_id=depose_par_id,
        client_id=client_id,
        statut_analyse=statut_a_l_enregistrement(),
    )
    db.add(fichier)
    await db.commit()
    await db.refresh(fichier)
    return fichier


async def fichier_par_cle(db: AsyncSession, cle_stockage: str) -> FichierDepose | None:
    result = await db.execute(
        select(FichierDepose).where(FichierDepose.cle_stockage == cle_stockage)
    )
    return result.scalar_one_or_none()


async def est_telechargeable(db: AsyncSession, cle_stockage: str) -> bool:
    """Le fichier peut-il être délivré ?

    UN FICHIER INCONNU DU REGISTRE EST DÉLIVRÉ. Ce n'est pas un oubli : tous les
    livrables stockés avant la création du registre sont dans ce cas, et les
    refuser rendrait indisponible d'un coup l'intégralité des documents déjà
    déposés en production. Le registre ne se remplit qu'en avant.

    La conséquence est assumée et bornée : ces fichiers-là n'ont jamais été
    analysés, mais ils ne l'auraient pas été davantage sans registre. Les
    nouveaux dépôts, eux, passent par la règle.
    """
    fichier = await fichier_par_cle(db, cle_stockage)
    if fichier is None:
        return True
    return fichier.statut_analyse == StatutAnalyse.SAIN


# Balise posée par GuardDuty sur chaque objet analysé. Nom confirmé en
# production le 2026-08-05, sur un dépôt de test étiqueté en moins de 45 s.
BALISE_GUARDDUTY = "GuardDutyMalwareScanStatus"

# Les CINQ statuts que GuardDuty peut rendre, et non deux.
#
# `UNSUPPORTED`, `ACCESS_DENIED` et `FAILED` ne sont ni sains ni rejetés, et les
# ranger dans l'un des deux serait faux dans les deux sens : « sain »
# délivrerait un fichier jamais vérifié, « rejeté » accuserait un fichier
# probablement inoffensif. Ils vont donc en `indetermine` — un état terminal qui
# n'ouvre pas le téléchargement et qui se voit.
_CORRESPONDANCE = {
    "NO_THREATS_FOUND": StatutAnalyse.SAIN,
    "THREATS_FOUND": StatutAnalyse.REJETE,
    "UNSUPPORTED": StatutAnalyse.INDETERMINE,
    "ACCESS_DENIED": StatutAnalyse.INDETERMINE,
    "FAILED": StatutAnalyse.INDETERMINE,
}


def statut_depuis_balise(valeur: str) -> StatutAnalyse:
    """Traduit une valeur de balise GuardDuty en état du registre.

    UNE VALEUR INCONNUE DEVIENT `indetermine`, JAMAIS `sain`. AWS peut ajouter un
    statut demain ; le défaut doit rester fermé. Ouvrir sur l'inconnu serait
    délivrer un fichier sur la foi d'une valeur qu'on ne sait pas interpréter.
    """
    return _CORRESPONDANCE.get(valeur.strip().upper(), StatutAnalyse.INDETERMINE)


async def enregistrer_verdict(
    db: AsyncSession, *, cle_stockage: str, balise: str
) -> FichierDepose | None:
    """Consigne le résultat de l'analyse pour un fichier du registre.

    Prend la valeur BRUTE de la balise GuardDuty plutôt qu'un booléen. La
    première version prenait `sain: bool` et ne pouvait donc exprimer que deux
    des cinq réponses possibles — un scan en échec y devenait « rejeté » ou
    « sain » selon l'appelant, les deux étant faux.

    Renvoie `None` si la clé est inconnue — un verdict portant sur un objet
    qu'on n'a pas enregistré ne doit pas créer de ligne : ce serait accepter
    comme source de vérité un appel dont on ne maîtrise pas l'origine.
    """
    fichier = await fichier_par_cle(db, cle_stockage)
    if fichier is None:
        return None
    fichier.statut_analyse = statut_depuis_balise(balise)
    fichier.analyse_le = datetime.now(UTC)
    await db.commit()
    await db.refresh(fichier)
    return fichier


DELAI_RENONCEMENT_ANALYSE = timedelta(hours=1)


async def rafraichir_analyses(
    db: AsyncSession, now: datetime, delai_renoncement: timedelta = DELAI_RENONCEMENT_ANALYSE
) -> dict[str, int]:
    """Relit la balise GuardDuty des fichiers encore en analyse. Renvoie les compteurs.

    POURQUOI RELIRE PLUTOT QU'ECOUTER. EventBridge supposerait une cible : une
    Lambda (infrastructure absente du projet), un endpoint HTTP (qu'il faudrait
    authentifier, faute de quoi n'importe qui pourrait annoncer qu'un fichier est
    sain — le trou même que ce chantier ferme, rouvert par la porte de service),
    ou une file SQS (qu'il faudrait interroger, donc sonder quand même).

    La relecture inverse le sens de la confiance : c'est NOUS qui allons lire,
    avec nos propres identifiants IAM. Rien d'extérieur n'affirme quoi que ce
    soit. Et sans détecteur GuardDuty dans le compte — vérifié le 2026-08-05 —
    la balise est de toute façon déjà le seul canal de vérité.

    LE COUT EST BORNE PAR CONSTRUCTION. Seuls les fichiers `en_analyse` sont
    interrogés : aucun fichier en attente, aucun appel S3. Le délai de
    renoncement est ce qui garantit cette borne dans le temps — sans lui, un
    objet que GuardDuty n'étiquette jamais serait relu à chaque passage,
    indéfiniment, et c'est la seule façon dont ce travail pourrait finir par
    coûter quelque chose.

    Un fichier abandonné passe en `indetermine` et non en `sain` : il devient
    visible au lieu de rester indiscernable d'un scan en cours.
    """
    from app.services import storage

    resultat = await db.execute(
        select(FichierDepose).where(FichierDepose.statut_analyse == StatutAnalyse.EN_ANALYSE)
    )
    en_attente = list(resultat.scalars().all())

    compteurs = {"lus": 0, "tranches": 0, "abandonnes": 0}
    for fichier in en_attente:
        try:
            balise = storage.lire_balise(fichier.cle_stockage, BALISE_GUARDDUTY)
        except Exception as exc:  # noqa: BLE001 — un fichier ne doit pas bloquer les autres
            logger.warning("Relecture d'analyse : échec sur {} ({})", fichier.cle_stockage, exc)
            continue
        compteurs["lus"] += 1

        if balise is not None:
            fichier.statut_analyse = statut_depuis_balise(balise)
            fichier.analyse_le = now
            compteurs["tranches"] += 1
        elif now - fichier.depose_le > delai_renoncement:
            fichier.statut_analyse = StatutAnalyse.INDETERMINE
            fichier.analyse_le = now
            compteurs["abandonnes"] += 1
            logger.warning(
                "Analyse abandonnée après {} : {}", delai_renoncement, fichier.cle_stockage
            )

    if compteurs["tranches"] or compteurs["abandonnes"]:
        await db.commit()
    return compteurs


DELAI_ORPHELIN_JOURS = 7


async def purger_orphelins(
    db: AsyncSession, now: datetime, delai_jours: int = DELAI_ORPHELIN_JOURS
) -> int:
    """Efface les fichiers déposés que plus rien ne référence. Renvoie le compte.

    UN ORPHELIN, C'EST QUOI. Le dépôt renvoie une clé de stockage, puis un second
    appel crée le livrable qui la référence. Entre les deux, rien ne garantit que
    le second arrive : un abandon en cours de route, un onglet fermé, une erreur
    réseau, et le fichier reste sur S3 sans qu'aucun livrable ne le désigne. Il
    n'a alors plus aucune finalité — c'est le cas le plus simple de l'article
    5-1-e du RGPD, et le seul qui ne prête à aucune discussion.

    POURQUOI UN DÉLAI DE GRÂCE. Purger immédiatement casserait le flux normal :
    entre le dépôt et la création du livrable il s'écoule quelques secondes, mais
    rien n'interdit à un utilisateur de laisser le formulaire ouvert. Sept jours
    laissent la place à toutes les lenteurs plausibles sans conserver ce qui ne
    sert à rien.

    L'ORDRE EST LE POINT CRITIQUE. On efface l'objet stocké, PUIS la ligne. Si la
    suppression de l'objet échoue, la ligne reste et le prochain passage
    réessaiera. L'ordre inverse perdrait la trace d'un fichier toujours présent
    sur S3 — soit exactement le problème que ce registre a été créé pour
    résoudre, réintroduit par l'autre bout.

    Un échec sur un fichier n'interrompt pas les autres : une clé illisible ne
    doit pas geler la purge de tout le reste.
    """
    from app.models.rssi_deliverable import RssiDeliverable
    from app.services import storage

    limite = now - timedelta(days=delai_jours)
    referencees = select(RssiDeliverable.file_url).where(RssiDeliverable.file_url.is_not(None))
    resultat = await db.execute(
        select(FichierDepose).where(
            FichierDepose.depose_le < limite,
            FichierDepose.cle_stockage.not_in(referencees),
        )
    )
    orphelins = list(resultat.scalars().all())

    purges = 0
    for fichier in orphelins:
        try:
            storage.supprimer_fichier(fichier.cle_stockage)
        except Exception as exc:  # noqa: BLE001 — un fichier ne doit pas bloquer les autres
            logger.warning(
                "Purge des orphelins : échec sur {}, ligne conservée pour réessai ({})",
                fichier.cle_stockage,
                exc,
            )
            continue
        await db.delete(fichier)
        purges += 1

    if purges:
        await db.commit()
    return purges


async def octets_deposes_par_client(db: AsyncSession, client_id: int) -> int:
    """Somme des tailles déposées pour un client — socle du futur quota."""
    result = await db.execute(
        select(FichierDepose.taille_octets).where(FichierDepose.client_id == client_id)
    )
    return sum(result.scalars().all())


class QuotaDepassementError(ValueError):
    """Le client a atteint son plafond de stockage."""

    def __init__(self, utilise: int, quota: int) -> None:
        self.utilise = utilise
        self.quota = quota
        super().__init__(
            f"Quota de dépôt atteint — {utilise // (1024 * 1024)} Mo utilisés "
            f"sur {quota // (1024 * 1024)} Mo. Supprimez un document ou "
            f"contactez votre consultant."
        )


async def verifier_quota(db: AsyncSession, client_id: int, taille_ajoutee: int) -> None:
    """Refuse un dépôt qui ferait dépasser le quota du client.

    POURQUOI UN QUOTA. `docs/DEPOT_DOCUMENTS.md` pose la contrainte : le dépôt
    doit rester attaché à un objet, jamais devenir un espace de stockage. Sans
    plafond, un abonné dispose d'un disque illimité et la facture S3 suit.
    Ouvrir le dépôt aux clients est le moment où ça cesse d'être théorique.

    Vérifié AVANT d'écrire sur S3 : refuser après stockage laisserait l'objet
    en place tout en annonçant un refus, et il faudrait le rattraper.
    """
    utilise = await octets_deposes_par_client(db, client_id)
    if utilise + taille_ajoutee > settings.QUOTA_DEPOT_CLIENT_OCTETS:
        raise QuotaDepassementError(utilise, settings.QUOTA_DEPOT_CLIENT_OCTETS)
