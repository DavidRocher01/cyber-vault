from datetime import datetime

from pydantic import BaseModel

from app.schemas.base import StrictModel

# --- Plans ---


class PlanOut(BaseModel):
    id: int
    name: str
    display_name: str
    price_eur: int
    # Prix annuel en centimes (2 mois offerts) et disponibilite reelle de la
    # facturation annuelle (dependante du price_id Stripe annuel). Exposes en
    # lecture pour piloter le selecteur mensuel/annuel du front.
    price_eur_yearly: int
    yearly_available: bool = False
    max_sites: int
    scan_interval_days: int
    tier_level: int
    allow_conformity_export: bool = True

    model_config = {"from_attributes": True}


# --- Subscriptions ---


class SubscriptionOut(BaseModel):
    id: int
    status: str
    current_period_end: datetime | None
    plan: PlanOut
    extra_sites: int = 0

    model_config = {"from_attributes": True}

    @property
    def effective_max_sites(self) -> int:
        return self.plan.max_sites + self.extra_sites


class CheckoutSessionOut(BaseModel):
    checkout_url: str


# --- Sites ---


class SiteCreate(StrictModel):
    url: str
    name: str
    rssi_client_id: int | None = None


class SiteOut(BaseModel):
    id: int
    url: str
    name: str
    is_active: bool
    created_at: datetime
    rssi_client_id: int | None = None

    model_config = {"from_attributes": True}


# --- Scans ---


class ScanOut(BaseModel):
    id: int
    site_id: int
    status: str
    overall_status: str | None
    pdf_path: str | None
    results_json: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}


class ScanTriggerOut(BaseModel):
    scan_id: int
    message: str


class PaginatedScans(BaseModel):
    items: list[ScanOut]
    total: int
    page: int
    per_page: int
    pages: int


# --- Code Scans ---


class CodeScanCreate(StrictModel):
    repo_url: str
    github_token: str | None = None  # optional PAT for private repos


class CodeScanOut(BaseModel):
    id: int
    user_id: int
    repo_url: str
    repo_name: str | None
    status: str
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    results_json: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class CodeScanTriggerOut(BaseModel):
    scan_id: int
    message: str


class PaginatedCodeScans(BaseModel):
    items: list[CodeScanOut]
    total: int
    page: int
    per_page: int
    pages: int


# ── Verification de domaine et sous-domaines ──────────────────────────────────
#
# Ces reponses etaient renvoyees sous forme de dictionnaires, donc invisibles au
# schema OpenAPI et jamais validees. Les typer a revele un ecart REEL : selon la
# branche empruntee, `SubdomainResultOut.total_found` etait present ou absent,
# alors que le frontend le declare obligatoire. La valeur par defaut ci-dessous
# force les deux chemins a s'accorder.


class DomainStatusOut(BaseModel):
    """Etat de verification d'un domaine.

    PARTAGE ENTRE `sites.py` ET `phishing.py`, qui renvoyaient la meme forme
    chacun de son cote. Le nom est volontairement neutre : la verification de
    domaine n'appartient a aucun des deux.
    """

    domain: str
    verified: bool
    verified_at: str | None = None


class DomainVerifyOut(BaseModel):
    domain: str
    verified: bool
    verification_token: str
    dns_record_name: str
    dns_record_type: str
    dns_record_value: str
    instructions: str


class ZoneTransferOut(BaseModel):
    vulnerable: bool
    nameservers: list[str] = []
    records_found: list[str] = []


class SubdomainEntryOut(BaseModel):
    subdomain: str
    ip: str = ""


class SubdomainResultOut(BaseModel):
    site_url: str
    subdomains: list[SubdomainEntryOut] = []
    zone_transfer: ZoneTransferOut | None = None
    # DEFAUT DELIBERE : la branche « aucun scan termine » ne renvoyait pas ce
    # champ, que le frontend attend pourtant toujours.
    total_found: int = 0
    scan_date: datetime | None = None


class FindingStatusOut(BaseModel):
    """Etat de traitement d'un constat, tel que l'ecran le lit."""

    module_key: str
    status: str
    note: str | None = None
    updated_at: str
