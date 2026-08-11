"""Reponses du module de simulation de phishing.

Ces endpoints renvoyaient des dictionnaires : invisibles au schema OpenAPI, donc
a toute verification de contrat, et surtout NI VALIDES NI FILTRES — un champ
ajoute a un serialiseur partait chez le client sans decision. Sur un module qui
manipule des adresses de collaborateurs et leurs reactions a un faux courriel,
c'est exactement ce qu'il ne faut pas laisser au hasard.

DEUX SERIALISEURS SERVENT HUIT ENDPOINTS (`_serialize_campaign`,
`_serialize_target`) : deux schemas suffisent donc a en couvrir la majorite.
"""

from pydantic import BaseModel


class PhishingTargetOut(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None
    department: str | None = None
    scenario_key: str | None = None
    status: str
    email_sent_at: str | None = None
    opened_at: str | None = None
    clicked_at: str | None = None
    submitted_at: str | None = None


class PhishingCampaignOut(BaseModel):
    id: int
    sending_domain: str | None = None
    name: str
    status: str
    # PIEGE DE NOMMAGE, TROUVE EN TYPANT. `plan_tier` est une CHAINE — le nom de
    # l'offre de phishing (`express`, `standard`, `premium`) — et n'a rien a voir
    # avec le `tier_level` numerique des abonnements. Le schema initial le
    # declarait entier ; cinquante tests sont tombes d'un coup.
    plan_tier: str | None = None
    rssi_client_id: int | None = None
    training_on_fail: bool = False
    training_trigger: str | None = None
    batch_size: int | None = None
    domain: str | None = None
    domain_verified: bool = False
    lookalike_domain: str | None = None
    scenario_keys: list[str] = []
    targets_count: int = 0
    emails_sent: int = 0
    opened_count: int = 0
    clicked_count: int = 0
    submitted_count: int = 0
    click_rate: float = 0
    cgu_accepted: bool = False
    scheduled_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str


class PhishingCampaignDetailOut(PhishingCampaignOut):
    """La campagne AVEC ses cibles — c'est la vue de detail."""

    targets: list[PhishingTargetOut] = []


class LookalikeSuggestionOut(BaseModel):
    """Un domaine ressemblant propose pour une campagne.

    SECONDE SUPPOSITION FAUSSE DE MA PART, corrigee par le typage : j'avais
    declare `suggestions: list[str]`, alors que chaque entree est un OBJET —
    `to_dict()` de `domain_lookalike.py` en produit sept champs. Deux tests sont
    tombes, et ils avaient raison.
    """

    domain: str
    technique: str
    realism_score: int = 0
    requires_purchase: bool = False
    purchase_url: str = ""
    setup_instructions: str = ""
    note: str = ""


class LookalikeDomainsOut(BaseModel):
    domain: str
    suggestions: list[LookalikeSuggestionOut] = []


class CampaignLaunchOut(BaseModel):
    status: str
    campaign_id: int


class TargetsUploadOut(BaseModel):
    targets_added: int
    targets_skipped: int
    targets_total: int
