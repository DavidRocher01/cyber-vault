"""Schemas, constantes et aides partages par les routes phishing."""

import re
from datetime import datetime

from fastapi import HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import safe_json_load
from app.models.enums import CampaignStatus
from app.models.phishing import (
    PhishingCampaign,
    PhishingTarget,
)
from app.services.phishing import campaigns, sending

# Plafond de lecture, aligne sur le dossier Dark Web (remediation S4).
_MAX_CSV_BYTES = 2 * 1024 * 1024

# Conserve une référence forte aux tâches détachées : sans cela, asyncio peut
# les garbage-collecter avant la fin (la tâche serait annulée silencieusement).
_background_tasks: set = set()

_MAX_TARGETS = {
    "express": 50,
    "standard": 200,
    "premium": 500,
    "quarterly": 100,
    "monthly": 300,
}

_VALID_TIERS = set(_MAX_TARGETS.keys())

# Mode entreprise directe : tier minimum requis pour lancer une campagne
# (1=Gratuit, 2=Starter, 3=Pro, 4=Business). Le mode consultant y accède via sa
# prestation (ownership du client), pas via ce gate.
_PHISHING_MIN_TIER = 3


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

# Domaine = labels ASCII + TLD alpha. Rejette IP littérales (TLD alpha), ports,
# chemins. Validé côté format UNIQUEMENT (pas de résolution DNS) : un domaine
# look-alike premium fraîchement enregistré peut ne pas encore résoudre.
_HOSTNAME_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$",
    re.IGNORECASE,
)


def _normalize_domain(value: str | None) -> str | None:
    """Valide un domaine fourni par l'utilisateur et renvoie le host nu.

    Anti-SSRF/anti-injection : tolère un préfixe https:// (le seul), rejette tout
    autre schéma (javascript:/data:/file:/http:...), port, chemin, espace,
    localhost et IP littérale. Ne fait AUCUNE requête réseau.
    """
    if value is None:
        return None
    v = value.strip()
    if not v:
        return None
    if v.lower().startswith("https://"):
        v = v[len("https://") :]
    if "://" in v or "/" in v or ":" in v or any(c.isspace() for c in v):
        raise ValueError("Indiquer un domaine seul (https accepté, sans port ni chemin)")
    if not _HOSTNAME_RE.match(v):
        raise ValueError("Domaine invalide (ex : connexion-entreprise.com)")
    return v


class CampaignCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., min_length=2, max_length=100)
    plan_tier: str = Field(..., pattern="^(express|standard|premium|quarterly|monthly)$")
    # Mode consultant : rattache la campagne à un client RSSI. NULL = entreprise directe.
    rssi_client_id: int | None = None


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(None, min_length=2, max_length=100)
    domain: str | None = Field(None, max_length=255)
    lookalike_domain: str | None = Field(None, max_length=255)
    scenario_keys: list[str] | None = None
    cgu_accepted: bool | None = None
    scheduled_at: datetime | None = None
    training_on_fail: bool | None = None
    training_trigger: str | None = Field(None, pattern="^(click|submit)$")
    batch_size: int | None = Field(None, ge=1, le=1000)

    @field_validator("domain", "lookalike_domain")
    @classmethod
    def _validate_domains(cls, v: str | None) -> str | None:
        return _normalize_domain(v)


class DomainVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str = Field(..., min_length=3, max_length=255)

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, v: str) -> str:
        return _normalize_domain(v)  # type: ignore[return-value]


class DomainCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str

    @field_validator("domain")
    @classmethod
    def _validate_domain(cls, v: str) -> str:
        return _normalize_domain(v)  # type: ignore[return-value]


class TargetAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    first_name: str | None = Field(None, max_length=100)
    last_name: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)


# Groupes de statuts de campagne — source unique (évite les tuples magiques
# dupliqués et divergents). Tous typés sur CampaignStatus.
# Modifier les cibles : uniquement avant lancement.
_EDITABLE_TARGET_STATUSES = (
    CampaignStatus.DRAFT,
    CampaignStatus.PENDING_VERIFICATION,
    CampaignStatus.READY,
)
# Modifier / lancer la campagne : idem + planifiée.
_EDITABLE_CAMPAIGN_STATUSES = (*_EDITABLE_TARGET_STATUSES, CampaignStatus.SCHEDULED)
# Annuler : avant/pendant l'envoi (pas depuis active/completed/cancelled, états terminaux).
_CANCELLABLE_STATUSES = (*_EDITABLE_CAMPAIGN_STATUSES, CampaignStatus.SENDING)
# Rapport PDF : uniquement quand l'envoi est terminé.
_REPORTABLE_STATUSES = (CampaignStatus.ACTIVE, CampaignStatus.COMPLETED)

# Message partagé (édition des cibles refusée hors des statuts éditables).
_TARGETS_LOCKED_DETAIL = "Impossible de modifier les cibles d'une campagne active ou terminée."


def _require_status(
    campaign: PhishingCampaign, allowed: tuple[CampaignStatus, ...], detail: str
) -> None:
    """Lève un 400 si la campagne n'est pas dans l'un des statuts autorisés."""
    if campaign.status not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sending_domain(c: PhishingCampaign) -> str:
    """Host depuis lequel partent les liens de la campagne (transparence UI).
    Sous-domaine maîtrisé par défaut ; look-alike si un jour renseigné."""
    racine = sending._tracking_base(c)  # ex: https://rochercybersecurite.com/api/v1
    return racine.split("://", 1)[-1].split("/", 1)[0]


def _serialize_campaign(c: PhishingCampaign) -> dict:
    return {
        "id": c.id,
        "sending_domain": _sending_domain(c),
        "name": c.name,
        "status": c.status,
        "plan_tier": c.plan_tier,
        "rssi_client_id": c.rssi_client_id,
        "training_on_fail": c.training_on_fail,
        "training_trigger": c.training_trigger,
        "batch_size": c.batch_size,
        "domain": c.domain,
        "domain_verified": c.domain_verified,
        "lookalike_domain": c.lookalike_domain,
        "scenario_keys": safe_json_load(c.scenario_keys, []),
        "targets_count": c.targets_count,
        "emails_sent": c.emails_sent,
        "opened_count": c.opened_count,
        "clicked_count": c.clicked_count,
        "submitted_count": c.submitted_count,
        "click_rate": round(c.clicked_count / c.targets_count, 4) if c.targets_count else 0,
        "cgu_accepted": c.cgu_accepted,
        "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
        "started_at": c.started_at.isoformat() if c.started_at else None,
        "finished_at": c.finished_at.isoformat() if c.finished_at else None,
        "created_at": c.created_at.isoformat(),
    }


def _serialize_target(t: PhishingTarget) -> dict:
    def _iso(dt: object) -> str | None:
        return dt.isoformat() if dt else None  # type: ignore[union-attr]

    return {
        "id": t.id,
        "email": t.email,
        "first_name": t.first_name,
        "last_name": t.last_name,
        "department": t.department,
        "scenario_key": t.scenario_key,
        "status": t.status,
        "email_sent_at": _iso(t.email_sent_at),
        "opened_at": _iso(t.opened_at),
        "clicked_at": _iso(t.clicked_at),
        "submitted_at": _iso(t.submitted_at),
    }


async def _get_owned(campaign_id: int, user_id: int, db: AsyncSession) -> PhishingCampaign:
    campaign = await campaigns.get_campaign(campaign_id, user_id, db)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campagne introuvable")
    return campaign
