from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.acquisition import ProvenanceIn
from app.schemas.base import StrictModel


class PublicScanCreate(StrictModel, ProvenanceIn):
    """Le scan gratuit est la première étape du tunnel : c'est ici qu'on relève
    la provenance, une fois, plutôt que de suivre le visiteur (`ProvenanceIn`)."""

    url: str


class PublicScanUnlockIn(StrictModel):
    """Déblocage du rapport complet : email + consentement RGPD obligatoire."""

    email: EmailStr
    consent: bool


class PublicScanOut(BaseModel):
    token: str
    status: str
    overall_status: str | None = None
    # Verrouillé tant que le rapport n'a pas été débloqué par email : results_json est
    # alors None et seul severity_counts (teaser agrégé, aucun détail) est exposé.
    locked: bool = True
    severity_counts: dict[str, int] | None = None
    results_json: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, obj, *, severity_counts: dict[str, int] | None = None) -> "PublicScanOut":
        unlocked = obj.email_consent_at is not None
        return cls(
            token=obj.session_token,
            status=obj.status,
            overall_status=obj.overall_status,
            locked=not unlocked,
            severity_counts=severity_counts,
            results_json=obj.results_json if unlocked else None,
            error_message=obj.error_message,
            created_at=obj.created_at,
            started_at=obj.started_at,
            finished_at=obj.finished_at,
        )
