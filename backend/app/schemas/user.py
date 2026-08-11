from pydantic import BaseModel, EmailStr, Field

from app.schemas.acquisition import ProvenanceIn
from app.schemas.base import StrictModel


class UserCreate(StrictModel, ProvenanceIn):
    """L'inscription porte la provenance quand l'utilisateur n'est pas passé par
    le scan gratuit — sinon elle est déjà connue et sera rattachée au compte."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(StrictModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class LoginOut(BaseModel):
    """Returned when 2FA is required before issuing tokens."""

    requires_2fa: bool = True


class UserOut(BaseModel):
    id: int
    email: EmailStr
    is_active: bool
    totp_enabled: bool = False
    is_rssi_consultant: bool = False
    # Administration de la plateforme. Exposé pour que le front sache s'il doit
    # ouvrir le back-office sans redemander de clé — le droit reste vérifié
    # côté serveur à chaque appel, ce champ ne fait qu'éviter un écran inutile.
    is_admin: bool = False
    # True si le compte est rattaché à un RssiClient (client_user_id) — sert au routage
    # post-connexion vers l'espace client. Calculé dans l'endpoint (pas une colonne).
    is_portal_client: bool = False

    model_config = {"from_attributes": True}


class NotificationPreferencesOut(BaseModel):
    notif_scan_done: bool
    notif_scan_critical: bool
    notif_url_scan_done: bool
    notif_code_scan_done: bool
    notif_ssl_expiry: bool

    model_config = {"from_attributes": True}


class NotificationPreferencesIn(StrictModel):
    notif_scan_done: bool
    notif_scan_critical: bool
    notif_url_scan_done: bool
    notif_code_scan_done: bool
    notif_ssl_expiry: bool


class AccessTokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    crypto_salt: str | None = None  # base64-encoded 32-byte salt for client-side PBKDF2


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(StrictModel):
    refresh_token: str


class ForgotPasswordIn(StrictModel):
    email: EmailStr


class ResetPasswordIn(StrictModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class BadgeGamificationOut(BaseModel):
    """Un badge de gamification, CALCULE a la volee depuis l'activite.

    A NE PAS CONFONDRE AVEC `BadgeOut` (schemas/awareness.py), qui decrit les
    badges de sensibilisation, persistes en base et portant `earned_at` sans
    `earned`. Deux concepts distincts sous un nom voisin : c'est exactement ce
    qui a fait rapprocher a tort ces deux types le 2026-08-10, faute de
    `response_model` ici pour lever l'ambiguite.
    """

    id: str
    label: str
    description: str
    icon: str
    earned: bool
    earned_at: str | None = None


class TwoFactorSetupOut(BaseModel):
    qr_code_b64: str  # base64 PNG
    secret: str  # manual entry fallback


class TwoFactorSetupIn(StrictModel):
    current_code: str | None = None  # required when 2FA is already active


class TwoFactorVerifyIn(StrictModel):
    code: str  # 6-digit TOTP code


class TwoFactorDisableIn(StrictModel):
    password: str
    code: str  # TOTP code required to disable
