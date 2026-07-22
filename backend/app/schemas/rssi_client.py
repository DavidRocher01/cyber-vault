"""Schemas Pydantic du module RSSI externalise (clients).

Extraits de l'endpoint rssi/clients.py (qui melangeait schemas + CRUD +
agregation) pour respecter la convention : les schemas vivent dans schemas/.
Re-exportes par clients.py pour ne pas casser les imports existants.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

ClientFormula = Literal["essentiel", "premium", "excellence"]
ClientStatus = Literal["active", "inactive", "churned"]


class RssiClientCreate(BaseModel):
    name: str
    email: str | None = None
    description: str | None = None
    formula: ClientFormula | None = None
    monthly_amount: float | None = None
    contract_start_date: date | None = None
    contract_renewal_at: date | None = None
    notion_workspace_url: str | None = None
    pipedrive_deal_id: str | None = None
    pennylane_customer_id: str | None = None


class RssiClientUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    description: str | None = None
    formula: ClientFormula | None = None
    monthly_amount: float | None = None
    contract_start_date: date | None = None
    contract_renewal_at: date | None = None
    status: ClientStatus | None = None
    notion_workspace_url: str | None = None
    pipedrive_deal_id: str | None = None
    pennylane_customer_id: str | None = None


class RssiClientOut(BaseModel):
    id: int
    name: str
    email: str | None
    description: str | None
    formula: str | None
    monthly_amount: float | None
    contract_start_date: date | None
    contract_renewal_at: date | None
    status: str
    notion_workspace_url: str | None
    pipedrive_deal_id: str | None
    pennylane_customer_id: str | None
    awareness_organization_id: int | None
    created_at: datetime
    updated_at: datetime | None
    sites_count: int
    worst_status: str | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


class RssiSiteOut(BaseModel):
    id: int
    url: str
    name: str
    is_active: bool
    created_at: datetime
    latest_scan_status: str | None
    last_scan_at: datetime | None

    model_config = {"from_attributes": False}


class UnlinkedSiteOut(BaseModel):
    id: int
    url: str
    name: str

    model_config = {"from_attributes": True}
