import asyncio
import base64
from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Cookie,
    Depends,
    HTTPException,
    Request,
    Response,
    status,
)
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.datetime_utils import ensure_utc
from app.core.limiter import limiter
from app.core.security import (
    REFRESH_TOKEN_EXPIRE_DAYS,
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.schemas.user import (
    AccessTokenOut,
    ForgotPasswordIn,
    ResetPasswordIn,
    UserCreate,
    UserLogin,
    UserOut,
)
from app.services import auth_service
from app.services.email_service import send_password_reset

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_NAME = "refresh_token"
_COOKIE_PATH = "/api/v1/auth"
_COOKIE_MAX_AGE = REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    response.set_cookie(
        key=_COOKIE_NAME,
        value=raw_refresh,
        httponly=True,
        secure=settings.APP_ENV == "production",
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=_COOKIE_NAME, path=_COOKIE_PATH)


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte",
    responses={
        409: {"description": "Email déjà utilisé"},
        429: {"description": "Trop de tentatives (5/min)"},
    },
)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    if await auth_service.get_user_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = await auth_service.create_user(
        db,
        email=payload.email,
        hashed_password=await asyncio.to_thread(hash_password, payload.password),
    )
    logger.info("New user registered (id={})", user.id)
    return user


@router.post(
    "/login",
    summary="Connexion (email + mot de passe, 2FA optionnelle)",
    response_description="Access token + crypto_salt ; ou {requires_2fa: true} si la 2FA est active",
    responses={
        401: {"description": "Identifiants ou code 2FA invalides"},
        429: {"description": "Compte verrouillé ou rate-limit (10/min)"},
    },
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.get_user_by_email(db, payload.email)

    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
    )

    if not user:
        raise invalid_exc

    now_utc = datetime.now(UTC)
    locked_until = ensure_utc(user.locked_until)
    if locked_until and locked_until > now_utc:
        remaining = int((locked_until - now_utc).total_seconds() / 60) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Compte verrouillé. Réessayez dans {remaining} minute(s).",
        )

    if not await asyncio.to_thread(verify_password, payload.password, user.hashed_password):
        # Commit avant de lever (dans le service) — sinon le compteur serait annulé.
        locked = await auth_service.register_failed_attempt(db, user)
        if locked:
            logger.warning(
                f"Account locked after {user.failed_login_attempts} attempts: user_id={user.id}"
            )
        raise invalid_exc

    # 2FA check — auto-repair inconsistent state (enabled=True but no secret)
    if user.totp_enabled and not user.totp_secret:
        user.totp_enabled = False

    if user.totp_enabled and user.totp_secret:
        if not payload.totp_code:
            # Mot de passe OK mais 2FA en attente : on ne réinitialise PAS encore le
            # compteur (sinon le brute-force du code TOTP ne serait jamais verrouillé).
            await auth_service.commit(db)
            return {"requires_2fa": True}
        import pyotp

        from app.core.totp_crypto import decrypt_totp_secret

        totp = pyotp.TOTP(decrypt_totp_secret(user.totp_secret))
        if not totp.verify(payload.totp_code, valid_window=1):
            # Les échecs TOTP comptent dans le lockout (anti brute-force du code 2FA).
            locked = await auth_service.register_failed_attempt(db, user)
            if locked:
                logger.warning(
                    f"Account locked after {user.failed_login_attempts} failed TOTP attempts: "
                    f"user_id={user.id}"
                )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Code 2FA invalide"
            )

    # Authentification complète réussie (mot de passe + 2FA le cas échéant) → reset compteur
    access_token = create_access_token(subject=str(user.id))
    raw_refresh = create_refresh_token()
    expires = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await auth_service.finalize_successful_login(
        db, user=user, raw_token=raw_refresh, expires=expires
    )
    _set_refresh_cookie(response, raw_refresh)
    logger.info("User logged in (id={})", user.id)
    return AccessTokenOut(
        access_token=access_token,
        crypto_salt=base64.b64encode(user.crypto_salt).decode() if user.crypto_salt else None,
    )


@router.post(
    "/refresh",
    response_model=AccessTokenOut,
    summary="Renouveler l'access token",
    response_description="Nouvel access token (le refresh token cookie est aussi tourné)",
    responses={401: {"description": "Refresh token absent, expiré ou révoqué"}},
)
async def refresh(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
    )
    if not refresh_token:
        raise invalid_exc
    stored = await auth_service.get_refresh_token(db, refresh_token)
    expires_at = ensure_utc(stored.expires_at if stored else None)
    if not stored or stored.revoked or (expires_at is not None and expires_at < datetime.now(UTC)):
        raise invalid_exc

    new_access = create_access_token(subject=str(stored.user_id))
    new_raw_refresh = create_refresh_token()
    new_expires = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await auth_service.rotate_refresh_token(
        db, stored=stored, raw_token=new_raw_refresh, expires=new_expires
    )
    _set_refresh_cookie(response, new_raw_refresh)
    return AccessTokenOut(access_token=new_access)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Déconnexion (révoque le refresh token + efface le cookie)",
)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        stored = await auth_service.get_refresh_token(db, refresh_token)
        if stored and not stored.revoked:
            await auth_service.revoke_refresh_token(db, stored)
    _clear_refresh_cookie(response)


RESET_TOKEN_EXPIRE_MINUTES = 30


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Demander un lien de réinitialisation",
    response_description="202 systématique (pas d'énumération de comptes)",
    responses={429: {"description": "Rate-limit (5/min)"}},
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await auth_service.get_user_by_email(db, payload.email)
    # Always return 202 to avoid user enumeration
    if not user:
        return

    raw_token = create_refresh_token()
    expires = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    await auth_service.create_reset_token(db, user_id=user.id, raw_token=raw_token, expires=expires)

    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={raw_token}"
    background_tasks.add_task(send_password_reset, user.email, reset_url)
    logger.info(f"Password reset requested for: user_id={user.id}")


@router.post(
    "/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Réinitialiser le mot de passe via token",
    response_description="204 ; révoque toutes les sessions et déverrouille le compte",
    responses={
        400: {"description": "Lien invalide ou expiré"},
        429: {"description": "Rate-limit (5/min)"},
    },
)
@limiter.limit("5/minute")
async def reset_password(
    request: Request, payload: ResetPasswordIn, db: AsyncSession = Depends(get_db)
):
    stored = await auth_service.get_reset_token(db, payload.token)

    invalid_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Lien invalide ou expiré",
    )

    expires_at = ensure_utc(stored.expires_at if stored else None)
    if not stored or stored.used or (expires_at is not None and expires_at < datetime.now(UTC)):
        raise invalid_exc

    user = await auth_service.get_user_by_id(db, stored.user_id)
    if not user:
        raise invalid_exc

    hashed = await asyncio.to_thread(hash_password, payload.password)
    await auth_service.apply_password_reset(db, user=user, hashed_password=hashed)
    logger.info(f"Password reset completed for user_id={user.id}")
