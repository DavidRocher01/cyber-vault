from pydantic import BaseModel, EmailStr


class NewsletterSubscribeIn(BaseModel):
    email: EmailStr


class NewsletterSubscribeOut(BaseModel):
    message: str
