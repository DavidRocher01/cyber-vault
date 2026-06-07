from typing import Literal

from pydantic import BaseModel, EmailStr


class ApiWaitlistIn(BaseModel):
    model_config = {"extra": "forbid"}

    email: EmailStr
    role: Literal["msp", "devsecops", "saas", "other"]
    company: str | None = None


class ApiWaitlistOut(BaseModel):
    count: int
