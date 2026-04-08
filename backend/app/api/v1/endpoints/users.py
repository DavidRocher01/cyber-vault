import base64
import io

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.user import UserOut, TwoFactorSetupOut, TwoFactorVerifyIn, TwoFactorDisableIn
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/users", tags=["users"])


class EmailUpdate(BaseModel):
    email: EmailStr
    current_password: str


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserOut)
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/email", response_model=UserOut)
async def update_email(
    payload: EmailUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect")

    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    current_user.email = payload.email
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    payload: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe actuel incorrect")
    if len(payload.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Le mot de passe doit faire au moins 8 caractères")

    current_user.hashed_password = hash_password(payload.new_password)
    await db.commit()


# ── Two-Factor Authentication ────────────────────────────────────────────────

def _make_qr_b64(uri: str) -> str:
    """Return a base64-encoded PNG QR code for the given OTP provisioning URI."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.post("/me/2fa/setup", response_model=TwoFactorSetupOut)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new TOTP secret and return QR code. Does NOT enable 2FA yet."""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="CyberScan")

    # Store the pending secret (not yet active)
    current_user.totp_secret = secret
    await db.commit()

    return TwoFactorSetupOut(qr_code_b64=_make_qr_b64(uri), secret=secret)


@router.post("/me/2fa/enable", response_model=UserOut)
async def enable_2fa(
    payload: TwoFactorVerifyIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code and enable 2FA for the account."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Lancez d'abord la configuration 2FA")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code invalide ou expiré")
    current_user.totp_enabled = True
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.post("/me/2fa/disable", response_model=UserOut)
async def disable_2fa(
    payload: TwoFactorDisableIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA after verifying password + current TOTP code."""
    if not verify_password(payload.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="La double authentification n'est pas activée")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code 2FA invalide")
    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()
    await db.refresh(current_user)
    return current_user
