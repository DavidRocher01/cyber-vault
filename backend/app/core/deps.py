import secrets

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.awareness_learner import AwarenessLearner
from app.models.user import User
from app.services.awareness_magic_link import decode_learner_jwt

bearer = HTTPBearer(auto_error=False)


def require_admin(x_admin_key: str = Header(default="")) -> None:
    """Dependency shared by all admin endpoints — validates the X-Admin-Key header."""
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(
        x_admin_key, settings.ADMIN_API_KEY
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")
    token = credentials.credentials
    user_id = decode_access_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token invalide")
    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur introuvable"
        )
    return user


async def get_current_learner(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AwarenessLearner:
    """Dependency for learner-authenticated endpoints (magic-link JWT)."""
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Non authentifié")
    payload = decode_learner_jwt(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token learner invalide"
        )
    learner_id = int(payload["sub"])
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.id == learner_id,
            AwarenessLearner.is_active == True,
        )
    )
    learner = result.scalar_one_or_none()
    if learner is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Learner introuvable")
    return learner


async def get_rssi_consultant(
    current_user: User = Depends(get_current_user),
) -> User:
    """Returns the current user only if they are a RSSI consultant."""
    if not current_user.is_rssi_consultant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux consultants RSSI",
        )
    return current_user


async def get_current_rssi_client(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Résout LE client RSSI rattaché au compte connecté (portail client).

    Socle d'isolation : toute requête du portail est scopée au RssiClient dont
    client_user_id == user courant. 403 si le compte n'est lié à aucun client.
    Retourne un RssiClient.
    """
    from app.models.rssi_client import RssiClient

    result = await db.execute(
        select(RssiClient).where(RssiClient.client_user_id == current_user.id)
    )
    client = result.scalar_one_or_none()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux clients suivis par un consultant RSSI",
        )
    return client


def require_min_tier(min_tier: int):
    """Factory de dépendance : autorise la route seulement si le plan actif de
    l'utilisateur a un tier_level >= min_tier, sinon 403.

    Le gating vit ici (couche transverse) mais délègue la lecture du tier au service
    (subscription_service.get_active_tier). Utilisation :
        @router.post(..., dependencies=[Depends(require_min_tier(2))])

    Tiers : 1=Gratuit, 2=Starter, 3=Pro, 4=Business.
    """

    async def _dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        # Import local pour éviter un cycle (services -> models -> ...).
        from app.services.subscription_service import get_active_tier

        tier = await get_active_tier(db, current_user.id)
        if tier < min_tier:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cette fonctionnalité nécessite un abonnement supérieur.",
            )

    return _dependency
