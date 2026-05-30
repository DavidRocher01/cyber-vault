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
from sqlalchemy import select
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
    hash_token,
    verify_password,
)
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.user import (
    AccessTokenOut,
    ForgotPasswordIn,
    ResetPasswordIn,
    UserCreate,
    UserLogin,
    UserOut,
)
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


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.commit()
    logger.info("New user registered (id={})", user.id)
    return user


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    payload: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

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

    if not verify_password(payload.password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            user.locked_until = datetime.now(UTC) + timedelta(minutes=settings.LOCKOUT_MINUTES)
            logger.warning(
                f"Account locked after {user.failed_login_attempts} attempts: user_id={user.id}"
            )
        await db.commit()  # Must commit before raising — rollback would undo the counter
        raise invalid_exc

    user.failed_login_attempts = 0
    user.locked_until = None

    # 2FA check — auto-repair inconsistent state (enabled=True but no secret)
    if user.totp_enabled and not user.totp_secret:
        user.totp_enabled = False

    if user.totp_enabled and user.totp_secret:
        if not payload.totp_code:
            await db.commit()
            return {"requires_2fa": True}
        import pyotp

        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(payload.totp_code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Code 2FA invalide"
            )

    access_token = create_access_token(subject=str(user.id))
    raw_refresh = create_refresh_token()
    expires = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(user_id=user.id, token=hash_token(raw_refresh), expires_at=expires))
    await db.commit()
    _set_refresh_cookie(response, raw_refresh)
    logger.info("User logged in (id={})", user.id)
    return AccessTokenOut(access_token=access_token)


@router.post("/refresh", response_model=AccessTokenOut)
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
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == hash_token(refresh_token))
    )
    stored = result.scalar_one_or_none()
    expires_at = ensure_utc(stored.expires_at if stored else None)
    if not stored or stored.revoked or (expires_at is not None and expires_at < datetime.now(UTC)):
        raise invalid_exc

    stored.revoked = True
    new_access = create_access_token(subject=str(stored.user_id))
    new_raw_refresh = create_refresh_token()
    new_expires = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(
        RefreshToken(
            user_id=stored.user_id,
            token=hash_token(new_raw_refresh),
            expires_at=new_expires,
        )
    )
    await db.commit()
    _set_refresh_cookie(response, new_raw_refresh)
    return AccessTokenOut(access_token=new_access)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token: str | None = Cookie(default=None, alias=_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    if refresh_token:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == hash_token(refresh_token))
        )
        stored = result.scalar_one_or_none()
        if stored and not stored.revoked:
            stored.revoked = True
            await db.commit()
    _clear_refresh_cookie(response)


RESET_TOKEN_EXPIRE_MINUTES = 30


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    payload: ForgotPasswordIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    # Always return 202 to avoid user enumeration
    if not user:
        return

    raw_token = create_refresh_token()
    expires = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_EXPIRE_MINUTES)
    db.add(PasswordResetToken(user_id=user.id, token=hash_token(raw_token), expires_at=expires))
    await db.commit()

    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={raw_token}"
    background_tasks.add_task(send_password_reset, user.email, reset_url)
    logger.info(f"Password reset requested for: user_id={user.id}")


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(payload: ResetPasswordIn, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == hash_token(payload.token))
    )
    stored = result.scalar_one_or_none()

    invalid_exc = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Lien invalide ou expiré",
    )

    expires_at = ensure_utc(stored.expires_at if stored else None)
    if not stored or stored.used or (expires_at is not None and expires_at < datetime.now(UTC)):
        raise invalid_exc

    user_result = await db.execute(select(User).where(User.id == stored.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise invalid_exc

    user.hashed_password = hash_password(payload.password)
    stored.used = True
    await db.commit()
    logger.info(f"Password reset completed for user_id={user.id}")
