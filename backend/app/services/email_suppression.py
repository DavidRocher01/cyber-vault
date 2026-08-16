"""Adresses a ne plus solliciter — rebonds durs et plaintes.

POURQUOI CE MODULE EXISTE. Rien n'ecoutait ce que Resend renvoyait. Un e-mail
qui rebondit ne produit aucune trace ici : l'envoi part, il echoue chez le
destinataire, et personne ne l'apprend jamais.

CE QUE CA COUTE, ET POURQUOI CE N'EST PAS QU'UN CONFORT. Les fournisseurs de
messagerie notent les expediteurs sur la proportion de rebonds et de plaintes.
Continuer a ecrire a une adresse morte degrade cette note, et la degradation ne
se voit pas : elle se manifeste le jour ou les e-mails LEGITIMES — confirmation
d'inscription, reinitialisation de mot de passe, rapport de scan — partent en
indesirables. On decouvre alors un probleme installe depuis des mois.

C'est pour cela que ce module doit exister AVANT d'ouvrir le scan gratuit au
trafic : l'authentification du domaine est deja irreprochable, et le taux de
rebond est le seul levier qui reste pour abimer la reputation d'envoi.

CE QU'ON SUPPRIME, ET CE QU'ON NE SUPPRIME PAS. Un rebond DUR (adresse
inexistante) et une plainte (« ceci est un indesirable ») sont definitifs : on
n'ecrit plus. Un rebond SOUPLE — boite pleine, serveur momentanement indisponible
— ne l'est pas, et bloquer sur ce motif priverait un client d'un rapport pour une
boite pleine un mardi.
"""

from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_suppression import EmailSuppression

# Types d'evenements Resend qui justifient de ne plus ecrire.
MOTIFS_DEFINITIFS = {"email.bounced", "email.complained"}


def _normaliser(email: str) -> str:
    return (email or "").strip().lower()


async def enregistrer(
    db: AsyncSession,
    *,
    email: str,
    evenement: str,
    detail: str | None = None,
) -> EmailSuppression | None:
    """Note une adresse comme injoignable. Idempotent.

    Renvoie `None` si l'evenement ne justifie pas de suppression, ou si
    l'adresse y figure deja — un meme rebond peut etre notifie plusieurs fois.
    """
    if evenement not in MOTIFS_DEFINITIFS:
        return None

    adresse = _normaliser(email)
    if not adresse:
        return None

    existante = await db.scalar(select(EmailSuppression).where(EmailSuppression.email == adresse))
    if existante:
        return None

    suppression = EmailSuppression(
        email=adresse,
        evenement=evenement,
        detail=(detail or "")[:500] or None,
        constate_le=datetime.now(UTC),
    )
    db.add(suppression)
    await db.flush()
    # L'adresse n'est PAS journalisee : c'est une donnee personnelle, et le
    # motif suffit a comprendre ce qui se passe.
    logger.info(f"Adresse mise en suppression apres {evenement}")
    return suppression


async def est_supprimee(db: AsyncSession, email: str) -> bool:
    adresse = _normaliser(email)
    if not adresse:
        return False
    return (
        await db.scalar(select(EmailSuppression.id).where(EmailSuppression.email == adresse))
    ) is not None


async def lister(db: AsyncSession, limite: int = 100) -> list[EmailSuppression]:
    resultat = await db.execute(
        select(EmailSuppression).order_by(EmailSuppression.constate_le.desc()).limit(limite)
    )
    return list(resultat.scalars().all())
