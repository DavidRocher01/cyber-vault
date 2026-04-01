from pydantic import BaseModel


class VaultItemCreate(BaseModel):
    title: str
    username: str | None = None
    password_encrypted: str
    url: str | None = None
    notes: str | None = None


class VaultItemUpdate(BaseModel):
    title: str | None = None
    username: str | None = None
    password_encrypted: str | None = None
    url: str | None = None
    notes: str | None = None


class VaultItemOut(BaseModel):
    id: int
    title: str
    username: str | None
    password_encrypted: str
    url: str | None
    notes: str | None

    model_config = {"from_attributes": True}
