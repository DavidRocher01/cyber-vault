"""Accès DB des endpoints d'authentification.

L'endpoint garde les préoccupations HTTP et crypto : hachage/vérification du mot
de passe, génération des JWT/refresh tokens, vérification TOTP, cookies, machine
à états 2FA et levée des HTTPException. Ce service porte les requêtes et le
staging + commit des mutations, à partir de valeurs déjà préparées.

⚠️ Politique de verrouillage (à préserver) : `register_failed_attempt` incrémente
le compteur d'échecs, verrouille au-delà du seuil et COMMITTE — le commit DOIT
avoir lieu avant que l'endpoint ne lève le 401, sinon un rollback annulerait le
compteur et le brute-force ne serait jamais verrouillé.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_token
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User

# ── Utilisateurs ─────────────────────────────────────────────────────────────


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Utilisateur par email, sinon None."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Utilisateur par identifiant, sinon None."""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, *, email: str, hashed_password: str) -> User:
    """Crée un utilisateur et COMMITTE (mot de passe déjà haché par l'endpoint)."""
    user = User(email=email, hashed_password=hashed_password)
    db.add(user)
    await db.commit()
    return user


async def commit(db: AsyncSession) -> None:
    """Persiste les mutations posées en mémoire (ex : auto-réparation de l'état 2FA)."""
    await db.commit()


# ── Verrouillage / succès de connexion ───────────────────────────────────────


async def register_failed_attempt(db: AsyncSession, user: User) -> bool:
    """Incrémente le compteur d'échecs, verrouille au seuil, puis COMMITTE.

    Retourne True si le compte vient d'être verrouillé. Le commit avant retour
    est essentiel : l'endpoint lève ensuite un 401, et un rollback annulerait le
    compteur (le brute-force ne serait jamais verrouillé).
    """
    user.failed_login_attempts += 1
    locked = user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS
    if locked:
        user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.LOCKOUT_MINUTES)
    await db.commit()
    return locked


async def finalize_successful_login(
    db: AsyncSession, *, user: User, raw_token: str, expires: datetime
) -> None:
    """Réinitialise le verrouillage, enregistre le refresh token, puis COMMITTE."""
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(RefreshToken(user_id=user.id, token=hash_token(raw_token), expires_at=expires))
    await db.commit()


# ── Refresh tokens ───────────────────────────────────────────────────────────


async def get_refresh_token(db: AsyncSession, raw_token: str) -> RefreshToken | None:
    """Refresh token stocké correspondant au token brut, sinon None."""
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == hash_token(raw_token))
    )
    return result.scalar_one_or_none()


async def rotate_refresh_token(
    db: AsyncSession, *, stored: RefreshToken, raw_token: str, expires: datetime
) -> None:
    """Révoque l'ancien refresh token, en crée un nouveau, puis COMMITTE."""
    stored.revoked = True
    db.add(RefreshToken(user_id=stored.user_id, token=hash_token(raw_token), expires_at=expires))
    await db.commit()


async def revoke_refresh_token(db: AsyncSession, stored: RefreshToken) -> None:
    """Révoque un refresh token et COMMITTE."""
    stored.revoked = True
    await db.commit()


# ── Réinitialisation de mot de passe ─────────────────────────────────────────


async def create_reset_token(
    db: AsyncSession, *, user_id: int, raw_token: str, expires: datetime
) -> None:
    """Enregistre un token de réinitialisation et COMMITTE."""
    db.add(PasswordResetToken(user_id=user_id, token=hash_token(raw_token), expires_at=expires))
    await db.commit()


async def get_reset_token(db: AsyncSession, raw_token: str) -> PasswordResetToken | None:
    """Token de réinitialisation stocké correspondant au token brut, sinon None."""
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == hash_token(raw_token))
    )
    return result.scalar_one_or_none()


async def apply_password_reset(db: AsyncSession, *, user: User, hashed_password: str) -> None:
    """Applique le nouveau mot de passe, invalide toutes les sessions et tous les
    reset tokens de l'utilisateur, déverrouille le compte, puis COMMITTE.

    Sécurité : un reset doit invalider les sessions (l'attaquant potentiel perd
    ses sessions) et déverrouiller le compte.
    """
    user.hashed_password = hashed_password
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked.is_(False))
        .values(revoked=True)
    )
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used.is_(False))
        .values(used=True)
    )
    await db.commit()
