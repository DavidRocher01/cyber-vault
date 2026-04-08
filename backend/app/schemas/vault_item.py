from pydantic import BaseModel, Field


VALID_CATEGORIES = {"login", "card", "note", "wifi", "other"}


class VaultItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    username: str | None = Field(default=None, max_length=200)
    password_encrypted: str = Field(min_length=1, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=10000)
    category: str = Field(default="login", max_length=32)

    def model_post_init(self, __context: object) -> None:
        if self.category not in VALID_CATEGORIES:
            self.category = "login"


class VaultItemUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    username: str | None = Field(default=None, max_length=200)
    password_encrypted: str | None = Field(default=None, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=32)

    def model_post_init(self, __context: object) -> None:
        if self.category is not None and self.category not in VALID_CATEGORIES:
            self.category = "login"


class VaultItemOut(BaseModel):
    id: int
    title: str
    username: str | None
    password_encrypted: str
    url: str | None
    notes: str | None
    category: str = "login"

    model_config = {"from_attributes": True}
