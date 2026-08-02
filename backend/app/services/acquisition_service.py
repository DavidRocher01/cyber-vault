"""Enregistrement et lecture des sources d'acquisition.

Conception : `docs/ANALYTICS.md`. En un mot — on n'enregistre d'où vient
quelqu'un qu'au moment où il convertit, jamais en le suivant de page en page.

Ce module porte deux responsabilités seulement :
  - `enregistrer()` — écrire une conversion, avec des valeurs normalisées ;
  - les trois lectures de l'onglet Acquisition.
"""

import re
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.public_scan import PublicScan
from app.models.source_acquisition import SourceAcquisition
from app.models.subscription import Subscription

# Étapes du tunnel, dans l'ordre. Toute valeur hors de cette liste est refusée :
# un endpoint public qui accepte un libellé libre finit par en stocker n'importe
# quoi.
ETAPES = ("scan_gratuit", "email_debloque", "inscription", "abonnement")

# Les UTM viennent du client. On les borne strictement plutôt que de leur faire
# confiance : minuscules, jeu de caractères restreint, longueur plafonnée.
# Sans ça, `?utm_source=<2 ko de texte>` transforme la table en stockage gratuit.
_LONGUEUR_MAX = 64
_INTERDITS = re.compile(r"[^a-z0-9._-]+")


def normaliser(valeur: str | None) -> str | None:
    """Ramène une valeur cliente à une étiquette sûre, ou `None`.

    « LinkedIn » et « linkedin » doivent compter ensemble, sinon le tableau se
    dédouble et le classement par revenu ne veut plus rien dire.
    """
    if not valeur:
        return None
    propre = _INTERDITS.sub("-", valeur.strip().lower()).strip("-")
    return propre[:_LONGUEUR_MAX] or None


def domaine_referent(referer: str | None) -> str | None:
    """Domaine seul. Jamais l'URL complète : elle peut porter un terme de
    recherche ou un identifiant de session, donc de la donnée personnelle."""
    if not referer:
        return None
    try:
        hote = urlparse(referer).hostname
    except ValueError:
        return None
    if not hote:
        return None
    return normaliser(hote.removeprefix("www."))


def chemin_interne(page: str | None) -> str | None:
    """Route d'entrée sans query string — laquelle contiendrait les UTM,
    déjà stockés à part, et parfois autre chose."""
    if not page:
        return None
    chemin = urlparse(page).path or "/"
    if not chemin.startswith("/"):
        chemin = "/" + chemin
    return chemin[:128]


async def enregistrer(
    db: AsyncSession,
    *,
    evenement: str,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    referer: str | None = None,
    page_atterrissage: str | None = None,
    user_id: int | None = None,
    public_scan_id: int | None = None,
    montant_mensuel_cents: int | None = None,
    valider: bool = True,
) -> SourceAcquisition | None:
    """Écrit une conversion. Ne lève jamais.

    La mesure ne doit pas pouvoir casser ce qu'elle mesure : si l'écriture
    échoue, l'inscription ou le scan de l'utilisateur aboutit quand même. On
    perd une ligne de statistique, pas un client.

    ⚠️ **Appeler après que l'écriture métier a été validée.** Un `flush` seul ne
    suffit pas — la ligne serait annulée à la fermeture de la session, ce qui
    donnait un onglet désespérément vide — mais le `commit` valide aussi tout ce
    qui traînerait de non validé dans la même session. Aux points d'appel HTTP,
    le scan ou le compte est déjà en base.

    `valider=False` pour le webhook Stripe, qui valide lui-même à la toute fin,
    en même temps que son marqueur d'idempotence : commiter avant persisterait
    l'abonnement sans le marqueur, et un échec ultérieur ferait rejouer
    l'événement sur un abonnement déjà actif.
    """
    if evenement not in ETAPES:
        logger.warning(f"Étape d'acquisition inconnue, ignorée : {evenement!r}")
        return None
    try:
        ligne = SourceAcquisition(
            evenement=evenement,
            utm_source=normaliser(utm_source),
            utm_medium=normaliser(utm_medium),
            utm_campaign=normaliser(utm_campaign),
            referent_domaine=domaine_referent(referer),
            page_atterrissage=chemin_interne(page_atterrissage),
            user_id=user_id,
            public_scan_id=public_scan_id,
            montant_mensuel_cents=montant_mensuel_cents,
        )
        db.add(ligne)
        if valider:
            await db.commit()
        else:
            await db.flush()
        return ligne
    except Exception as exc:  # noqa: BLE001 — voir la docstring
        logger.warning(f"Acquisition non enregistrée ({evenement}) : {exc}")
        if valider:
            await db.rollback()
        return None


def _depuis(jours: int) -> datetime:
    return datetime.now(UTC) - timedelta(days=jours)


def _compte(etape: str):
    """Compteur conditionnel — une étape du tunnel dans un GROUP BY."""
    return func.count(case((SourceAcquisition.evenement == etape, 1)))


async def tunnel(db: AsyncSession, *, jours: int = 90) -> dict[str, int]:
    """Volumes par étape, toutes sources confondues."""
    resultat = await db.execute(
        select(SourceAcquisition.evenement, func.count())
        .where(SourceAcquisition.cree_le >= _depuis(jours))
        .group_by(SourceAcquisition.evenement)
    )
    compte = dict(resultat.all())
    return {etape: int(compte.get(etape, 0)) for etape in ETAPES}


async def par_source(db: AsyncSession, *, jours: int = 90) -> list[dict]:
    """Le tableau central : une ligne par source, triée par revenu.

    Le MRR est la somme des montants figés à l'abonnement, et non un calcul
    refait depuis la grille courante — sinon un changement de tarif réécrirait
    l'historique d'acquisition.
    """
    resultat = await db.execute(
        select(
            SourceAcquisition.utm_source,
            _compte("scan_gratuit").label("scans"),
            _compte("inscription").label("inscriptions"),
            _compte("abonnement").label("abonnements"),
            func.coalesce(func.sum(SourceAcquisition.montant_mensuel_cents), 0).label("mrr"),
        )
        .where(SourceAcquisition.cree_le >= _depuis(jours))
        .group_by(SourceAcquisition.utm_source)
        .order_by(func.coalesce(func.sum(SourceAcquisition.montant_mensuel_cents), 0).desc())
    )
    lignes = []
    for source, scans, inscriptions, abonnements, mrr in resultat.all():
        lignes.append(
            {
                "source": source or "direct",
                "scans": int(scans),
                "inscriptions": int(inscriptions),
                "abonnements": int(abonnements),
                "mrr_cents": int(mrr),
                # Du scan à l'abonnement : le seul taux qui parle d'argent.
                "taux_conversion": round(abonnements / scans * 100, 1) if scans else 0.0,
            }
        )
    return lignes


async def par_page(db: AsyncSession, *, jours: int = 90, limite: int = 10) -> list[dict]:
    """Pages d'entrée de ceux qui ont converti — pas le trafic brut, qu'on ne
    mesure pas."""
    resultat = await db.execute(
        select(
            SourceAcquisition.page_atterrissage,
            _compte("scan_gratuit").label("scans"),
            _compte("inscription").label("inscriptions"),
            _compte("abonnement").label("abonnements"),
        )
        .where(
            SourceAcquisition.cree_le >= _depuis(jours),
            SourceAcquisition.page_atterrissage.is_not(None),
        )
        .group_by(SourceAcquisition.page_atterrissage)
        .order_by(func.count().desc())
        .limit(limite)
    )
    return [
        {
            "page": page,
            "scans": int(scans),
            "inscriptions": int(inscriptions),
            "abonnements": int(abonnements),
        }
        for page, scans, inscriptions, abonnements in resultat.all()
    ]


async def rattacher_par_email(db: AsyncSession, *, email: str, user_id: int) -> int:
    """Relie les conversions anonymes d'un scan au compte cree ensuite.

    Sans ce rattachement, la chaine casse au milieu : la source vit sur la ligne
    du scan gratuit, qui n'a pas de `user_id`, tandis que l'inscription a un
    `user_id` mais pas de source. Le revenu ne pourrait alors jamais etre
    rattache au canal qui l'a produit.

    **Le lien passe par l'e-mail, pas par un identifiant d'appareil.** Rien
    n'est ecrit dans le navigateur : on rapproche deux actions volontaires de la
    meme personne — une adresse saisie pour recevoir un rapport, la meme adresse
    saisie pour creer un compte. C'est le seul recoupement que la conception
    autorise (cf. `docs/ANALYTICS.md`), et il ne relie aucune navigation.
    """
    scans = (
        (await db.execute(select(PublicScan.id).where(PublicScan.email == email))).scalars().all()
    )
    if not scans:
        return 0
    lignes = (
        (
            await db.execute(
                select(SourceAcquisition).where(
                    SourceAcquisition.public_scan_id.in_(scans),
                    SourceAcquisition.user_id.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    for ligne in lignes:
        ligne.user_id = user_id
    if lignes:
        await db.commit()
    return len(lignes)


async def source_du_compte(db: AsyncSession, *, user_id: int) -> dict[str, str | None]:
    """La provenance d'origine d'un compte : celle de sa PREMIERE ligne qui en
    porte une.

    Sert a faire heriter l'abonnement de la source qui l'a amene. Le webhook
    Stripe connait le montant, jamais le canal : sans cet heritage, tout le
    revenu atterrirait sous « direct » et le tableau serait faux sans le dire.
    """
    ligne = (
        await db.execute(
            select(SourceAcquisition)
            .where(
                SourceAcquisition.user_id == user_id,
                SourceAcquisition.utm_source.is_not(None),
            )
            .order_by(SourceAcquisition.cree_le.asc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if ligne is None:
        return {"utm_source": None, "utm_medium": None, "utm_campaign": None}
    return {
        "utm_source": ligne.utm_source,
        "utm_medium": ligne.utm_medium,
        "utm_campaign": ligne.utm_campaign,
    }


async def enregistrer_abonnement(
    db: AsyncSession, *, user_id: int, montant_mensuel_cents: int, valider: bool = True
) -> SourceAcquisition | None:
    """Derniere etape du tunnel, appelee depuis le webhook Stripe.

    Pas au clic sur « s'abonner » : a ce moment-la rien n'existe encore, on peut
    fermer l'onglet ou se faire refuser la carte. Compter les intentions
    gonflerait le revenu attribue, donc fausserait la decision d'investissement
    que ce tableau doit eclairer.
    """
    return await enregistrer(
        db,
        evenement="abonnement",
        user_id=user_id,
        montant_mensuel_cents=montant_mensuel_cents,
        valider=valider,
        **await source_du_compte(db, user_id=user_id),
    )


async def mrr_par_source_confirme(db: AsyncSession, *, jours: int = 90) -> int:
    """MRR total attribué, restreint aux abonnements ENCORE actifs.

    `par_source` somme ce qui a été signé sur la période ; ceci somme ce qui
    tourne encore. Les deux sont utiles et ne disent pas la même chose.
    """
    resultat = await db.execute(
        select(func.coalesce(func.sum(SourceAcquisition.montant_mensuel_cents), 0))
        .join(Subscription, Subscription.user_id == SourceAcquisition.user_id)
        .where(
            SourceAcquisition.evenement == "abonnement",
            SourceAcquisition.cree_le >= _depuis(jours),
            Subscription.status == "active",
        )
    )
    return int(resultat.scalar_one() or 0)
