from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator


class UrlScanCreate(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("L'URL doit commencer par http:// ou https://")
        return v


class UrlScanOut(BaseModel):
    id: int
    user_id: int
    url: str
    status: str
    verdict: str | None
    threat_type: str | None
    threat_score: int | None
    screenshot_path: str | None
    results_json: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class PaginatedUrlScans(BaseModel):
    items: list[UrlScanOut]
    total: int
    page: int
    per_page: int
    pages: int
