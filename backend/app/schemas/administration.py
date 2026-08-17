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
    # Sans ce champ, `response_model` le FILTRERAIT en silence : la console
    # d'administration afficherait des factures sans SIREN alors que la base le
    # porte. Le meme oubli s'est deja produit deux fois sur ce projet.
    client_siren: str | None = None
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


class AdminQuoteOut(BaseModel):
    id: int
    quote_number: str
    client_name: str
    client_email: str
    client_address: str | None = None
    subject: str
    items: list[dict] = []
    total_cents: int
    total_eur: float
    validity_days: int
    status: str
    issue_date: str
    created_at: str


class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    type: str
    client_name: str
    client_email: str
    client_address: str | None = None
    description: str
    amount_cents: int
    amount_eur: float
    status: str
    issue_date: str
    created_at: str


class PaginatedInvoicesOut(BaseModel):
    total: int
    page: int
    per_page: int
    pages: int
    items: list[InvoiceOut] = []


class AdminStatsOut(BaseModel):
    """Chiffres du tableau de bord d'administration.

    LES STRUCTURES IMBRIQUEES RESTENT EN `list[dict]`, DELIBEREMENT. Un
    `response_model` FILTRE : decrire a moitie `recent_contacts` ou
    `weekly_activity` en supprimerait les champs oublies, en silence. C'est
    l'erreur commise le 2026-08-11 sur `AdminUserOut`, qui a fait disparaitre
    deux champs de la reponse. On type ce qu'on a lu, on laisse passer le reste.
    """

    users_total: int
    active_subscriptions: int
    newsletter_subscribers: int
    bookings_this_month: int
    new_contacts: int
    recent_contacts: list[dict] = []
    recent_bookings: list[dict] = []
    weekly_activity: list[dict] = []
    revenue_per_month: list[dict] = []


class ContentSyncOut(BaseModel):
    """Synchronisation du catalogue de sensibilisation.

    DEUX ISSUES POSSIBLES : le compte rendu, ou un message d'erreur. Tous les
    champs sont donc optionnels plutot que d'imposer une union — l'appelant lit
    `error` en premier.
    """

    status: str | None = None
    programs: int | None = None
    modules: int | None = None
    errors: list[str] = []
    error: str | None = None


class QuoteDecisionOut(BaseModel):
    status: str
    quote_number: str
    already: bool = False


class ClientAwarenessOut(BaseModel):
    id: int
    name: str
    max_learners: int | None = None
    learner_count: int = 0
    already: bool = False


class PortalInviteOut(BaseModel):
    status: str
    email: str
    account_created: bool = False
    # Renseignee seulement hors production, pour permettre la recette sans boite
    # aux lettres.
    invite_url: str | None = None


class DeliverableUploadOut(BaseModel):
    key: str
    filename: str | None = None
    statut_analyse: str


class DeliverableUrlOut(BaseModel):
    url: str
