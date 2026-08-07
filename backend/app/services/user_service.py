"""Service d'acces aux donnees du compte utilisateur (profil, 2FA, RGPD).

L'endpoint garde la verification/hachage des mots de passe, la generation des
secrets TOTP, le rendu QR et la construction des reponses HTTP ; ce service
porte les requetes et les frontieres de transaction. Les fonctions recoivent
des valeurs deja preparees (email, hash, dict de champs), jamais un schema HTTP.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.brand_profile import BrandProfile
from app.models.code_scan import CodeScan
from app.models.darkweb_dossier import DarkwebDossier
from app.models.darkweb_scan import DarkwebScan
from app.models.invoice import Invoice
from app.models.iso27001_assessment import Iso27001Assessment
from app.models.nis2_assessment import Nis2Assessment
from app.models.notification import Notification
from app.models.quote import Quote
from app.models.rssi_client import RssiClient
from app.models.scan import Scan
from app.models.site import Site
from app.models.subscription import Subscription
from app.models.training_progress import TrainingProgress
from app.models.url_scan import UrlScan
from app.models.user import User
from app.services import auth_service


def _iso(dt: datetime | None) -> str | None:
    """Sérialise une date en ISO 8601, ou None."""
    return dt.isoformat() if dt else None


def _now() -> datetime:
    """Horodatage UTC courant (isolé pour faciliter le mock en test)."""
    from datetime import UTC

    return datetime.now(UTC)


# ── Profil ────────────────────────────────────────────────────────────────────


async def is_portal_client(db: AsyncSession, user_id: int) -> bool:
    """True si l'utilisateur est rattache a un client de portail RSSI."""
    linked = (
        await db.execute(select(RssiClient.id).where(RssiClient.client_user_id == user_id).limit(1))
    ).scalar_one_or_none()
    return linked is not None


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    """Utilisateur par email, sinon None."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def update_email(db: AsyncSession, user: User, email: str) -> User:
    """Met a jour l'email du compte et revoque toutes les sessions actives.

    Un changement de credential invalide les refresh tokens existants (G0-1) :
    un token vole ne doit pas survivre au changement d'email.
    """
    user.email = email
    await auth_service.revoke_all_sessions(db, user.id)
    await db.commit()
    await db.refresh(user)
    return user


async def update_password(db: AsyncSession, user: User, hashed_password: str) -> None:
    """Remplace le hash du mot de passe du compte et revoque toutes les sessions.

    Un changement de mot de passe invalide les refresh tokens existants (G0-0) :
    un token vole ne doit pas survivre au changement de mot de passe.
    """
    user.hashed_password = hashed_password
    await auth_service.revoke_all_sessions(db, user.id)
    await db.commit()


# ── RGPD (export / effacement) ────────────────────────────────────────────────


async def list_sites_for_user(db: AsyncSession, user_id: int) -> list[Site]:
    """Sites appartenant a l'utilisateur."""
    result = await db.execute(select(Site).where(Site.user_id == user_id))
    return list(result.scalars().all())


async def list_scans_for_sites(db: AsyncSession, site_ids: list[int]) -> list[Scan]:
    """Scans des sites fournis, du plus recent au plus ancien."""
    if not site_ids:
        return []
    result = await db.execute(
        select(Scan).where(Scan.site_id.in_(site_ids)).order_by(Scan.created_at.desc())
    )
    return list(result.scalars().all())


async def export_account_data(db: AsyncSession, user: User) -> dict:
    """Assemble l'export de portabilite RGPD (Art.20) du compte.

    Couvre les donnees personnelles/metier appartenant au titulaire du compte :
    identite, sites+scans, scans URL/code, conformite NIS2/ISO, sensibilisation,
    Dark Web (dossiers+cibles et scans simples), facturation (abonnement, factures,
    devis), marque et notifications. Le perimetre volontairement EXCLU est documente
    dans la cle `perimetre_exclu` :
      - le coffre-fort (vault) : blobs chiffres zero-knowledge, illisibles sans la cle
        cote client -> exportables uniquement via un dechiffrement navigateur ;
      - les donnees RSSI/awareness : PII de TIERS (salaries des clients) dont le
        titulaire est responsable de traitement, pas des donnees le concernant.
    Renvoie un dict de valeurs simples (aucun type HTTP) serialisable en JSON.
    """
    user_id = user.id

    sites = await list_sites_for_user(db, user_id)
    site_map = {s.id: s for s in sites}
    scans = await list_scans_for_sites(db, [s.id for s in sites])
    scans_data = [
        {
            "site_url": site_map[scan.site_id].url,
            "site_name": site_map[scan.site_id].name,
            "scan_id": scan.id,
            "status": scan.status,
            "overall_status": scan.overall_status,
            "created_at": _iso(scan.created_at),
            "finished_at": _iso(scan.finished_at),
        }
        for scan in scans
    ]

    # `client_id.is_(None)` : SON auto-evaluation, pas les dossiers qu'il a
    # montes pour ses clients.
    #
    # DEUX RAISONS, ET LA SECONDE EST LA PLUS IMPORTANTE. Sans ce filtre, un
    # consultant suivant plusieurs clients ferait remonter plusieurs lignes et
    # `scalar_one_or_none()` leverait : l'export de portabilite casserait
    # precisement pour les comptes qui se servent le plus du produit.
    # Et sur le fond, un dossier de conformite decrit l'entite du CLIENT. Le
    # verser dans l'export d'un autre compte publierait les donnees d'un tiers
    # dans un fichier de portabilite.
    nis2 = (
        await db.execute(
            select(Nis2Assessment).where(
                Nis2Assessment.user_id == user_id,
                Nis2Assessment.client_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    iso = (
        await db.execute(select(Iso27001Assessment).where(Iso27001Assessment.user_id == user_id))
    ).scalar_one_or_none()

    def _assessment(a: Nis2Assessment | Iso27001Assessment | None) -> dict | None:
        if a is None:
            return None
        return {
            "score": a.score,
            "items_json": a.items_json,
            "created_at": _iso(a.created_at),
            "updated_at": _iso(a.updated_at),
        }

    training = (
        (await db.execute(select(TrainingProgress).where(TrainingProgress.user_id == user_id)))
        .scalars()
        .all()
    )
    dossiers = (
        (
            await db.execute(
                select(DarkwebDossier)
                .where(DarkwebDossier.user_id == user_id)
                .options(selectinload(DarkwebDossier.targets))
            )
        )
        .scalars()
        .all()
    )
    darkweb_scans = (
        (await db.execute(select(DarkwebScan).where(DarkwebScan.user_id == user_id)))
        .scalars()
        .all()
    )
    subscription = (
        await db.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .options(selectinload(Subscription.plan))
        )
    ).scalar_one_or_none()
    invoices = (await db.execute(select(Invoice).where(Invoice.user_id == user_id))).scalars().all()
    quotes = (await db.execute(select(Quote).where(Quote.user_id == user_id))).scalars().all()
    brand = (
        await db.execute(select(BrandProfile).where(BrandProfile.user_id == user_id))
    ).scalar_one_or_none()
    notifications = (
        (await db.execute(select(Notification).where(Notification.user_id == user_id)))
        .scalars()
        .all()
    )
    url_scans = (
        (await db.execute(select(UrlScan).where(UrlScan.user_id == user_id))).scalars().all()
    )
    code_scans = (
        (await db.execute(select(CodeScan).where(CodeScan.user_id == user_id))).scalars().all()
    )

    return {
        "exported_at": _iso(_now()),
        "account": {
            "email": user.email,
            "is_active": user.is_active,
            "totp_enabled": user.totp_enabled,
        },
        "sites": [{"url": s.url, "name": s.name, "created_at": _iso(s.created_at)} for s in sites],
        "scans": scans_data,
        "url_scans": [
            {
                "url": u.url,
                "status": u.status,
                "verdict": u.verdict,
                "threat_type": u.threat_type,
                "threat_score": u.threat_score,
                "created_at": _iso(u.created_at),
                "finished_at": _iso(u.finished_at),
            }
            for u in url_scans
        ],
        "code_scans": [
            {
                "repo_url": c.repo_url,
                "repo_name": c.repo_name,
                "status": c.status,
                "critical_count": c.critical_count,
                "high_count": c.high_count,
                "medium_count": c.medium_count,
                "low_count": c.low_count,
                "created_at": _iso(c.created_at),
                "finished_at": _iso(c.finished_at),
            }
            for c in code_scans
        ],
        "nis2_assessment": _assessment(nis2),
        "iso27001_assessment": _assessment(iso),
        "training_progress": [
            {"module_id": t.module_id, "completed_at": _iso(t.completed_at)} for t in training
        ],
        "darkweb_dossiers": [
            {
                "company_name": d.company_name,
                "domain": d.domain,
                "status": d.status,
                "total_emails": d.total_emails,
                "exposed_emails": d.exposed_emails,
                "risk_score": d.risk_score,
                "severity_score": d.severity_score,
                "monitor_active": d.monitor_active,
                "created_at": _iso(d.created_at),
                "finished_at": _iso(d.finished_at),
                "targets": [
                    {
                        "email": t.email,
                        "status": t.status,
                        "check_status": t.check_status,
                        "total_breaches": t.total_breaches,
                        "checked_at": _iso(t.checked_at),
                    }
                    for t in d.targets
                ],
            }
            for d in dossiers
        ],
        "darkweb_scans": [
            {
                "email": s.email,
                "total_breaches": s.total_breaches,
                "status": s.status,
                "checked_at": _iso(s.checked_at),
            }
            for s in darkweb_scans
        ],
        "subscription": (
            {
                "plan": subscription.plan.name if subscription.plan else None,
                "status": subscription.status,
                "extra_sites": subscription.extra_sites,
                "current_period_start": _iso(subscription.current_period_start),
                "current_period_end": _iso(subscription.current_period_end),
                "created_at": _iso(subscription.created_at),
            }
            if subscription
            else None
        ),
        "invoices": [
            {
                "invoice_number": inv.invoice_number,
                "type": inv.type,
                "description": inv.description,
                "amount_cents": inv.amount_cents,
                "status": inv.status,
                "issue_date": _iso(inv.issue_date),
                "client_name": inv.client_name,
                "client_email": inv.client_email,
            }
            for inv in invoices
        ],
        "quotes": [
            {
                "quote_number": q.quote_number,
                "subject": q.subject,
                "items": q.items,
                "total_cents": q.total_cents,
                "status": q.status,
                "issue_date": _iso(q.issue_date),
                "client_name": q.client_name,
                "client_email": q.client_email,
            }
            for q in quotes
        ],
        "brand_profile": (
            {
                "company_name": brand.company_name,
                "accent_color": brand.accent_color,
                "updated_at": _iso(brand.updated_at),
            }
            if brand
            else None
        ),
        "notifications": [
            {
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "read": n.read,
                "created_at": _iso(n.created_at),
            }
            for n in notifications
        ],
        "perimetre_exclu": {
            "vault": (
                "Coffre-fort chiffre de bout en bout (zero-knowledge) : les entrees sont "
                "des blobs AES-GCM dechiffrables uniquement dans votre navigateur avec votre "
                "cle. Elles sont exportables depuis le module Coffre-fort apres deverrouillage."
            ),
            "rssi_awareness": (
                "Donnees RSSI externalise et sensibilisation : elles concernent les salaries "
                "de vos clients (tiers), dont vous etes responsable de traitement. Elles ne "
                "font pas partie de vos donnees personnelles au sens de l'Art.20 et sont "
                "disponibles via les modules dedies."
            ),
        },
    }


async def delete_account(db: AsyncSession, user: User) -> None:
    """Supprime le compte et toutes ses donnees associees (cascade)."""
    await db.delete(user)
    await db.commit()


# ── Preferences de notification ───────────────────────────────────────────────


async def update_notification_prefs(db: AsyncSession, user: User, values: dict) -> User:
    """Met a jour les preferences de notification (dict de champs modele)."""
    for field, value in values.items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return user


# ── Badges (gamification) ─────────────────────────────────────────────────────


async def list_done_scans_for_user(db: AsyncSession, user_id: int) -> list[Scan]:
    """Scans termines de l'utilisateur, tries par date de fin croissante."""
    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Site.user_id == user_id, Scan.status == "done")
        .order_by(Scan.finished_at.asc())
    )
    return list(result.scalars().all())


async def get_nis2_for_user(db: AsyncSession, user_id: int) -> Nis2Assessment | None:
    """SON auto-evaluation NIS2, sinon None.

    Meme filtre que l'export de portabilite, et pour les memes raisons : sans
    lui, un consultant suivant plusieurs clients ferait lever
    `scalar_one_or_none()`, et le score affiche sur son tableau de bord serait
    celui d'un client au lieu du sien.
    """
    result = await db.execute(
        select(Nis2Assessment).where(
            Nis2Assessment.user_id == user_id,
            Nis2Assessment.client_id.is_(None),
        )
    )
    return result.scalar_one_or_none()


# ── Double authentification (TOTP) ────────────────────────────────────────────


async def set_totp_secret(db: AsyncSession, user: User, encrypted_secret: str) -> None:
    """Enregistre la graine TOTP chiffree (pre-activation)."""
    user.totp_secret = encrypted_secret
    await db.commit()


async def enable_totp(db: AsyncSession, user: User) -> User:
    """Active la 2FA sur le compte."""
    user.totp_enabled = True
    await db.commit()
    await db.refresh(user)
    return user


async def disable_totp(db: AsyncSession, user: User) -> User:
    """Desactive la 2FA et efface la graine TOTP."""
    user.totp_enabled = False
    user.totp_secret = None
    await db.commit()
    await db.refresh(user)
    return user
