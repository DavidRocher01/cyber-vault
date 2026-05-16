from pydantic import BaseModel, EmailStr, field_validator

NEED_TYPES = {"audit-flash", "audit-app", "pentest", "abonnement", "autre"}


class ContactIn(BaseModel):
    name: str
    email: EmailStr
    phone: str | None = None
    need_type: str
    site_url: str | None = None
    message: str

    @field_validator("name")
    @classmethod
    def name_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Le nom doit contenir entre 2 et 100 caractères")
        return v

    @field_validator("message")
    @classmethod
    def message_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10 or len(v) > 2000:
            raise ValueError("Le message doit contenir entre 10 et 2000 caractères")
        return v

    @field_validator("need_type")
    @classmethod
    def valid_need(cls, v: str) -> str:
        if v not in NEED_TYPES:
            raise ValueError("Type de besoin invalide")
        return v

    @field_validator("phone")
    @classmethod
    def phone_length(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 20:
            raise ValueError("Numéro de téléphone trop long")
        return v.strip() if v else None

    @field_validator("site_url")
    @classmethod
    def site_url_length(cls, v: str | None) -> str | None:
        if v is not None and len(v.strip()) > 500:
            raise ValueError("URL trop longue")
        return v.strip() if v else None
