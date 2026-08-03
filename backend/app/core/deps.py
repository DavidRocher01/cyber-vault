from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.awareness_learner import AwarenessLearner
from app.models.user import User
from app.services.awareness_magic_link import decode_learner_jwt

bearer = HTTPBearer(auto_error=False)


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


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Accès au back-office : exige un compte portant `users.is_admin`.

    Le droit est attaché à une identité — traçable, révocable en désactivant le
    compte, et couvert par sa 2FA.

    Historique, parce que la forme de cette fonction s'explique par là : jusqu'au
    2026-08-02 elle acceptait aussi un en-tête `X-Admin-Key`, secret partagé
    statique sans identité ni révocation, relevé par l'audit du 2026-07-27. Cette
    voie a d'abord été neutralisée en production (la clé n'est plus injectée dans
    la task), puis retirée du code ici.

    Retourne l'utilisateur : les appelants peuvent ainsi tracer QUI agit, ce
    qu'un secret partagé ne permettait pas.
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs",
        )
    return current_user


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


async def require_conformity_export(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Autorise l'export des rapports de conformité (NIS2 / ISO 27001) seulement si le
    plan actif l'inclut (plans payants). Le Gratuit fait l'auto-évaluation mais n'exporte pas.

    Fail-open volontaire quand le plan est inconnu (plan Gratuit non semé, ex. tests) :
    on ne bloque que si l'on sait positivement que le plan actif interdit l'export. En prod
    le Gratuit est toujours semé (allow_conformity_export=False) → un compte gratuit ou
    sans abonnement (repli Gratuit) reçoit bien un 403.
    """
    from app.services.subscription_service import get_active_plan

    plan = await get_active_plan(db, current_user.id)
    if plan is not None and not plan.allow_conformity_export:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="L'export des rapports de conformité nécessite un abonnement payant.",
        )
