from pydantic import BaseModel, EmailStr, field_validator

from app.schemas.contact import NEED_TYPES


class SlotOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    date: str
    time: str
    duration_minutes: int
    label: str
    is_booked: bool


class SlotIn(BaseModel):
    date: str    # YYYY-MM-DD
    time: str    # HH:MM
    duration_minutes: int = 30
    label: str = "Appel découverte"

    @field_validator("date")
    @classmethod
    def valid_date(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("Format YYYY-MM-DD requis")
        return v

    @field_validator("time")
    @classmethod
    def valid_time(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("Format HH:MM requis")
        return v


class SlotBatchIn(BaseModel):
    slots: list[SlotIn]


class BookingIn(BaseModel):
    slot_id: int
    name: str
    email: EmailStr
    phone: str | None = None
    need_type: str
    message: str | None = None

    @field_validator("name")
    @classmethod
    def name_length(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Nom requis (2–100 caractères)")
        return v

    @field_validator("need_type")
    @classmethod
    def valid_need(cls, v: str) -> str:
        if v not in NEED_TYPES:
            raise ValueError("Type de besoin invalide")
        return v


class BookingOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    slot_id: int
    name: str
    email: str
    phone: str | None
    need_type: str
    message: str | None
    status: str
    created_at: str


class BookingConfirmOut(BaseModel):
    message: str
    booking_id: int
