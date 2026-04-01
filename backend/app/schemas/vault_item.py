from pydantic import BaseModel, Field


class VaultItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    username: str | None = Field(default=None, max_length=200)
    password_encrypted: str = Field(min_length=1, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=10000)


class VaultItemUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    username: str | None = Field(default=None, max_length=200)
    password_encrypted: str | None = Field(default=None, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=10000)


class VaultItemOut(BaseModel):
    id: int
    title: str
    username: str | None
    password_encrypted: str
    url: str | None
    notes: str | None

    model_config = {"from_attributes": True}
