from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
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

    model_config = {"from_attributes": True}


class NotificationPreferencesOut(BaseModel):
    notif_scan_done: bool
    notif_scan_critical: bool
    notif_url_scan_done: bool
    notif_code_scan_done: bool
    notif_ssl_expiry: bool

    model_config = {"from_attributes": True}


class NotificationPreferencesIn(BaseModel):
    notif_scan_done: bool
    notif_scan_critical: bool
    notif_url_scan_done: bool
    notif_code_scan_done: bool
    notif_ssl_expiry: bool


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshIn(BaseModel):
    refresh_token: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class TwoFactorSetupOut(BaseModel):
    qr_code_b64: str   # base64 PNG
    secret: str        # manual entry fallback


class TwoFactorVerifyIn(BaseModel):
    code: str          # 6-digit TOTP code


class TwoFactorDisableIn(BaseModel):
    password: str
    code: str          # TOTP code required to disable
