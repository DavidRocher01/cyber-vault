from datetime import datetime
from pydantic import BaseModel


class PublicScanCreate(BaseModel):
    url: str


class PublicScanOut(BaseModel):
    token: str
    status: str
    overall_status: str | None = None
    results_json: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj) -> "PublicScanOut":
        return cls(
            token=obj.session_token,
            status=obj.status,
            overall_status=obj.overall_status,
            results_json=obj.results_json,
            error_message=obj.error_message,
            created_at=obj.created_at,
            started_at=obj.started_at,
            finished_at=obj.finished_at,
        )
