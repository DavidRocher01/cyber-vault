"""Service d'acces aux donnees du compte utilisateur (profil, 2FA, RGPD).

L'endpoint garde la verification/hachage des mots de passe, la generation des
secrets TOTP, le rendu QR et la construction des reponses HTTP ; ce service
porte les requetes et les frontieres de transaction. Les fonctions recoivent
des valeurs deja preparees (email, hash, dict de champs), jamais un schema HTTP.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.nis2_assessment import Nis2Assessment
from app.models.rssi_client import RssiClient
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

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
    """Met a jour l'email du compte."""
    user.email = email
    await db.commit()
    await db.refresh(user)
    return user


async def update_password(db: AsyncSession, user: User, hashed_password: str) -> None:
    """Remplace le hash du mot de passe du compte."""
    user.hashed_password = hashed_password
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
    """Evaluation NIS2 de l'utilisateur, sinon None."""
    result = await db.execute(select(Nis2Assessment).where(Nis2Assessment.user_id == user_id))
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
