"""Reponses de la console d'administration, des factures et des reservations.

Ces endpoints renvoyaient des dictionnaires : ni valides ni filtres, et absents
du schema OpenAPI. Sur la console d'administration en particulier, ou circulent
adresses, statuts d'abonnement et droits, un champ ajoute par megarde a un
serialiseur partirait chez le client sans decision.
"""

from datetime import datetime

from pydantic import BaseModel


class MessageOut(BaseModel):
    """Reponse ne portant qu'un message destine a l'utilisateur."""

    message: str


class AdminInvoiceOut(BaseModel):
    id: int
    invoice_number: str
    type: str
    user_id: int | None = None
    client_name: str
    client_email: str
    client_address: str | None = None
    description: str
    amount_cents: int
    amount_eur: float
    status: str
    stripe_invoice_id: str | None = None
    issue_date: str
    created_at: str


class AdminUserOut(BaseModel):
    id: int
    email: str
    is_active: bool
    is_rssi_consultant: bool
    # UN DROIT D'ADMINISTRATION DOIT POUVOIR S'AUDITER : son absence de cette
    # liste avait fait conclure a tort, le 2026-08-02, qu'un compte n'en avait
    # pas. Le typer garantit qu'il ne disparaitra pas silencieusement.
    is_admin: bool = False
    totp_enabled: bool = False
    plan: str | None = None
    plan_name: str | None = None
    subscription_status: str | None = None
    subscription_since: str | None = None
    # LE « POURQUOI » DE L'ECART entre plan facture et plan applique. Sans ces
    # deux champs, un administrateur voit « Gratuit » sur un compte qu'il a
    # lui-meme passe en Business, sans aucun moyen de comprendre.
    #
    # ILS AVAIENT ETE OUBLIES DE CE SCHEMA, et le `response_model` les a donc
    # SUPPRIMES de la reponse : deux tests sont tombes. C'est le revers du
    # filtrage — un schema incomplet retire des donnees en silence.
    subscription_period_end: str | None = None
    subscription_perimee: bool = False


class AdminUserPlanOut(BaseModel):
    id: int
    plan: str
    plan_name: str
    max_sites: int
    scan_interval_days: int
    allow_conformity_export: bool


class AdminConsultantFlagOut(BaseModel):
    id: int
    is_rssi_consultant: bool


class MonitorToggleOut(BaseModel):
    monitor_active: bool
    # UN `datetime`, PAS UNE CHAINE : l endpoint renvoie l objet brut et laisse
    # FastAPI le serialiser. Declare `str` d abord, huit tests sont tombes.
    next_monitor_at: datetime | None = None


class CatalogSyncOut(BaseModel):
    synced: int
    message: str
