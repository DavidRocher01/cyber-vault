"""Reponses du tableau de bord de la console RSSI.

Ces cinq endpoints renvoyaient des dictionnaires. Consequence directe et
mesurable : les interfaces `DashboardOverview`, `ClientSummary`,
`DashboardAlert`, `CalendarEvent` et `DashboardSuggestion` du frontend
figuraient parmi celles SANS SCHEMA BACKEND CORRESPONDANT, donc hors de portee
de toute verification de contrat. Les typer les y ramene.

Les formes sont derivees de `aggregation_service.py`, seule source qui dise
ce qui est reellement renvoye.
"""

from pydantic import BaseModel


class DashboardOverviewOut(BaseModel):
    total_clients: int
    total_mrr: float
    open_actions: int
    overdue_actions: int
    renewals_upcoming: int
    upcoming_visits: int


class ClientSummaryOut(BaseModel):
    id: int
    name: str
    formula: str | None = None
    monthly_amount: float | None = None
    status: str | None = None
    contract_renewal_at: str | None = None
    open_actions: int = 0
    overdue_actions: int = 0
    next_visit: str | None = None


class DashboardAlertOut(BaseModel):
    type: str
    severity: str
    client_id: int | None = None
    client_name: str | None = None
    title: str
    detail: str | None = None


class CalendarEventOut(BaseModel):
    visit_id: int
    client_id: int | None = None
    client_name: str | None = None
    scheduled_date: str | None = None
    visit_type: str | None = None
    location: str | None = None


class DashboardSuggestionOut(BaseModel):
    type: str
    client_id: int | None = None
    client_name: str | None = None
    title: str
    reason: str | None = None
    cta: str | None = None
