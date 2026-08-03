"""Registre des fichiers déposés et verdict de l'analyse antivirus.

Ce service détient une seule règle, et c'est elle qui compte :
**un fichier n'est délivré que s'il est réputé sain.**

Le reste — l'enregistrement du dépôt, la réception du verdict — n'existe que
pour la rendre applicable. Cf. `docs/DEPOT_DOCUMENTS.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime

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


async def enregistrer_verdict(
    db: AsyncSession, *, cle_stockage: str, sain: bool
) -> FichierDepose | None:
    """Consigne le résultat de l'analyse pour un fichier du registre.

    Renvoie `None` si la clé est inconnue — un verdict portant sur un objet
    qu'on n'a pas enregistré ne doit pas créer de ligne : ce serait accepter
    comme source de vérité un appel dont on ne maîtrise pas l'origine.
    """
    fichier = await fichier_par_cle(db, cle_stockage)
    if fichier is None:
        return None
    fichier.statut_analyse = StatutAnalyse.SAIN if sain else StatutAnalyse.REJETE
    fichier.analyse_le = datetime.now(UTC)
    await db.commit()
    await db.refresh(fichier)
    return fichier


async def octets_deposes_par_client(db: AsyncSession, client_id: int) -> int:
    """Somme des tailles déposées pour un client — socle du futur quota."""
    result = await db.execute(
        select(FichierDepose.taille_octets).where(FichierDepose.client_id == client_id)
    )
    return sum(result.scalars().all())
