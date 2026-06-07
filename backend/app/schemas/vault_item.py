from pydantic import BaseModel, Field

VALID_CATEGORIES = {"login", "card", "note", "wifi", "other"}


class VaultItemCreate(BaseModel):
    model_config = {"extra": "forbid"}

    # Plain fields — optional/legacy. Zero-knowledge clients send only *_encrypted.
    title: str | None = Field(default=None, max_length=200)
    username: str | None = Field(default=None, max_length=200)
    password_encrypted: str = Field(min_length=0, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=10000)
    category: str = Field(default="login", max_length=32)
    # Zero-knowledge encrypted fields (opaque blobs — backend never reads content)
    title_encrypted: str | None = Field(default=None, max_length=16384)
    username_encrypted: str | None = Field(default=None, max_length=16384)
    url_encrypted: str | None = Field(default=None, max_length=16384)
    notes_encrypted: str | None = Field(default=None, max_length=65536)

    def model_post_init(self, __context: object) -> None:
        if self.category not in VALID_CATEGORIES:
            self.category = "login"


class VaultItemUpdate(BaseModel):
    model_config = {"extra": "forbid"}

    title: str | None = Field(default=None, max_length=200)
    username: str | None = Field(default=None, max_length=200)
    password_encrypted: str | None = Field(default=None, max_length=8192)
    url: str | None = Field(default=None, max_length=2048)
    notes: str | None = Field(default=None, max_length=10000)
    category: str | None = Field(default=None, max_length=32)
    title_encrypted: str | None = Field(default=None, max_length=16384)
    username_encrypted: str | None = Field(default=None, max_length=16384)
    url_encrypted: str | None = Field(default=None, max_length=16384)
    notes_encrypted: str | None = Field(default=None, max_length=65536)

    def model_post_init(self, __context: object) -> None:
        if self.category is not None and self.category not in VALID_CATEGORIES:
            self.category = "login"


class VaultItemOut(BaseModel):
    id: int
    title: str | None
    username: str | None
    password_encrypted: str
    url: str | None
    notes: str | None
    category: str = "login"
    # Encrypted fields returned as-is for zero-knowledge clients
    title_encrypted: str | None = None
    username_encrypted: str | None = None
    url_encrypted: str | None = None
    notes_encrypted: str | None = None

    model_config = {"from_attributes": True}
