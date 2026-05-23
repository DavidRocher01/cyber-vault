from datetime import datetime
from pydantic import BaseModel, HttpUrl


# --- Plans ---

class PlanOut(BaseModel):
    id: int
    name: str
    display_name: str
    price_eur: int
    max_sites: int
    scan_interval_days: int
    tier_level: int

    model_config = {"from_attributes": True}


# --- Subscriptions ---

class SubscriptionOut(BaseModel):
    id: int
    status: str
    current_period_end: datetime | None
    plan: PlanOut

    model_config = {"from_attributes": True}


class CheckoutSessionOut(BaseModel):
    checkout_url: str


# --- Sites ---

class SiteCreate(BaseModel):
    url: str
    name: str


class SiteOut(BaseModel):
    id: int
    url: str
    name: str
    is_active: bool
    created_at: datetime

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

class CodeScanCreate(BaseModel):
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
