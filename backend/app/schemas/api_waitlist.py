from typing import Literal

from pydantic import BaseModel, EmailStr

from app.schemas.base import StrictModel


class ApiWaitlistIn(StrictModel):
    email: EmailStr
    role: Literal["msp", "devsecops", "saas", "other"]
    company: str | None = None


class ApiWaitlistOut(BaseModel):
    count: int
