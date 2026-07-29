import asyncio
import base64
import io
import json
from datetime import UTC, datetime

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import hash_password, verify_password
from app.core.totp_crypto import decrypt_totp_secret, encrypt_totp_secret
from app.models.user import User
from app.schemas.user import (
    NotificationPreferencesIn,
    NotificationPreferencesOut,
    TwoFactorDisableIn,
    TwoFactorSetupIn,
    TwoFactorSetupOut,
    TwoFactorVerifyIn,
    UserOut,
)
from app.services import user_service


class DeleteAccountIn(BaseModel):
    password: str


router = APIRouter(prefix="/users", tags=["users"])


class EmailUpdate(BaseModel):
    email: EmailStr
    current_password: str


class PasswordUpdate(BaseModel):
    current_password: str
    new_password: str


@router.get("/me", response_model=UserOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    out = UserOut.model_validate(current_user)
    out.is_portal_client = await user_service.is_portal_client(db, current_user.id)
    return out


@router.put("/me/email", response_model=UserOut)
async def update_email(
    payload: EmailUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await asyncio.to_thread(
        verify_password, payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect"
        )

    if await user_service.get_by_email(db, payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email déjà utilisé")

    return await user_service.update_email(db, current_user, payload.email)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(
    payload: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await asyncio.to_thread(
        verify_password, payload.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mot de passe actuel incorrect",
        )
    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le mot de passe doit faire au moins 8 caractères",
        )

    hashed = await asyncio.to_thread(hash_password, payload.new_password)
    await user_service.update_password(db, current_user, hashed)


# ── Two-Factor Authentication ────────────────────────────────────────────────


def _make_qr_b64(uri: str) -> str:
    """Return a base64-encoded PNG QR code for the given OTP provisioning URI."""
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@router.get("/me/export")
async def export_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data as JSON (RGPD — droit à la portabilité, Art.20).

    Le périmètre complet (sites/scans, conformité, Dark Web, facturation, marque,
    notifications) et ce qui en est volontairement exclu sont assemblés côté service.
    """
    export = await user_service.export_account_data(db, current_user)
    content = json.dumps(export, ensure_ascii=False, indent=2)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={
            "Content-Disposition": "attachment; filename=rochercybersecurite_mes_donnees.json"
        },
    )


@router.delete("/me", status_code=204)
async def delete_my_account(
    payload: DeleteAccountIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete account and all associated data (RGPD — droit à l'effacement)."""
    if not await asyncio.to_thread(verify_password, payload.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Mot de passe incorrect"
        )

    await user_service.delete_account(db, current_user)


@router.get("/me/notification-preferences", response_model=NotificationPreferencesOut)
async def get_notification_preferences(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me/notification-preferences", response_model=NotificationPreferencesOut)
async def update_notification_preferences(
    payload: NotificationPreferencesIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.update_notification_prefs(
        db,
        current_user,
        {
            "notif_scan_done": payload.notif_scan_done,
            "notif_scan_critical": payload.notif_scan_critical,
            "notif_url_scan_done": payload.notif_url_scan_done,
            "notif_code_scan_done": payload.notif_code_scan_done,
            "notif_ssl_expiry": payload.notif_ssl_expiry,
        },
    )


@router.get("/me/badges")
async def get_my_badges(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the 5 gamification badges computed from existing data."""
    from datetime import timedelta

    now = datetime.now(UTC)
    since_30d = now - timedelta(days=30)

    done_scans = await user_service.list_done_scans_for_user(db, current_user.id)
    nis2 = await user_service.get_nis2_for_user(db, current_user.id)

    def _iso(dt) -> str | None:
        return dt.isoformat() if dt else None

    first = done_scans[0] if done_scans else None
    fifth = done_scans[4] if len(done_scans) >= 5 else None
    ok_scan = next((s for s in done_scans if s.overall_status == "OK"), None)
    recent = [s for s in done_scans if s.finished_at and s.finished_at >= since_30d]
    clean_30d = len(recent) > 0 and not any(s.overall_status == "CRITICAL" for s in recent)
    nis2_done = nis2 is not None and nis2.score > 0

    return [
        {
            "id": "first_scan",
            "label": "Premier scan",
            "description": "Votre première analyse de sécurité réalisée",
            "icon": "radar",
            "earned": first is not None,
            "earned_at": _iso(first.finished_at) if first else None,
        },
        {
            "id": "power_user",
            "label": "Analyste confirmé",
            "description": "5 analyses de sécurité réalisées",
            "icon": "analytics",
            "earned": len(done_scans) >= 5,
            "earned_at": _iso(fifth.finished_at) if fifth else None,
        },
        {
            "id": "site_secured",
            "label": "Site sécurisé",
            "description": "Au moins un scan avec résultat global OK",
            "icon": "verified_user",
            "earned": ok_scan is not None,
            "earned_at": _iso(ok_scan.finished_at) if ok_scan else None,
        },
        {
            "id": "no_critical_30d",
            "label": "30 jours propres",
            "description": "Aucune faille critique détectée sur 30 jours",
            "icon": "shield",
            "earned": clean_30d,
            "earned_at": None,
        },
        {
            "id": "nis2_complete",
            "label": "Conformité NIS2",
            "description": "Évaluation de conformité NIS2 complétée",
            "icon": "policy",
            "earned": nis2_done,
            "earned_at": _iso(nis2.updated_at) if nis2_done and nis2 else None,
        },
    ]


@router.post("/me/2fa/setup", response_model=TwoFactorSetupOut)
@limiter.limit("5/minute")
async def setup_2fa(
    request: Request,
    payload: TwoFactorSetupIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new TOTP secret and return QR code. Does NOT enable 2FA yet.
    If 2FA is already active, the current TOTP code must be provided to prevent
    account takeover via stolen JWT.
    """
    if current_user.totp_enabled:
        if not payload.current_code:
            raise HTTPException(
                status_code=400,
                detail="Code TOTP actuel requis pour reconfigurer la 2FA",
            )
        totp = pyotp.TOTP(decrypt_totp_secret(current_user.totp_secret))
        if not totp.verify(payload.current_code, valid_window=1):
            raise HTTPException(status_code=400, detail="Code TOTP invalide")

    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=current_user.email, issuer_name="Rocher Cybersécurité")

    # Graine chiffrée au repos ; le secret brut n'est renvoyé qu'ici (pré-activation,
    # nécessaire pour la saisie manuelle dans l'app d'authentification).
    await user_service.set_totp_secret(db, current_user, encrypt_totp_secret(secret))

    return TwoFactorSetupOut(qr_code_b64=_make_qr_b64(uri), secret=secret)


@router.post("/me/2fa/enable", response_model=UserOut)
@limiter.limit("5/minute")
async def enable_2fa(
    request: Request,
    payload: TwoFactorVerifyIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify a TOTP code and enable 2FA for the account."""
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Lancez d'abord la configuration 2FA")
    totp = pyotp.TOTP(decrypt_totp_secret(current_user.totp_secret))
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code invalide ou expiré")
    return await user_service.enable_totp(db, current_user)


@router.post("/me/2fa/disable", response_model=UserOut)
@limiter.limit("5/minute")
async def disable_2fa(
    request: Request,
    payload: TwoFactorDisableIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA after verifying password + current TOTP code."""
    if not await asyncio.to_thread(verify_password, payload.password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")
    if not current_user.totp_enabled or not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="La double authentification n'est pas activée")
    totp = pyotp.TOTP(decrypt_totp_secret(current_user.totp_secret))
    if not totp.verify(payload.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Code 2FA invalide")
    return await user_service.disable_totp(db, current_user)
