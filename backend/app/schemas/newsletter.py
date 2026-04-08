from datetime import datetime

from pydantic import BaseModel, EmailStr


class NewsletterSubscribeIn(BaseModel):
    email: EmailStr


class NewsletterSubscribeOut(BaseModel):
    message: str


# Admin schemas
class SubscriberOut(BaseModel):
    id: int
    email: str
    subscribed_at: datetime
    confirmed_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


class NewsletterStatsOut(BaseModel):
    total: int
    active: int
    pending_confirmation: int


class SendIssueIn(BaseModel):
    edition: int
    flash_title: str
    flash_body: str
    reflex_title: str
    reflex_body: str
    legal_title: str
    legal_body: str


class SendIssueOut(BaseModel):
    sent: int
    message: str
