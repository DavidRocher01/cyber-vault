from pydantic import BaseModel, EmailStr
from typing import Literal


class ApiWaitlistIn(BaseModel):
    email: EmailStr
    role: Literal["msp", "devsecops", "saas", "other"]
    company: str | None = None


class ApiWaitlistOut(BaseModel):
    count: int
