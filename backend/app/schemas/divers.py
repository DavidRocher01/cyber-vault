"""Reponses des endpoints restants — sonde, webhooks, quiz, quotas, exports.

Dernier lot d'epuration de la dette de contrat. LA REGLE RETENUE EST SANS
JUGEMENT : on ne dispense de `response_model` que ce qui ne PEUT PAS avoir de
schema JSON — aucun corps, un fichier, un flux. « C'est du developpement » ou
« ca n'interesse personne » sont des criteres qui pourrissent : dans six mois,
plus personne ne sait si l'exception tient encore.

C'est pourquoi `health.py` et `dev_testing.py` sont types comme le reste.
"""

from datetime import datetime

from pydantic import BaseModel


class SignedUrlOut(BaseModel):
    """Lien de telechargement signe, a duree limitee.

    Quatre endpoints renvoyaient exactement cette forme, chacun de son cote :
    pieces NIS2 (compte propre et dossier client), livrables RSSI, portail
    client. Un seul schema les decrit desormais.
    """

    url: str


class StatusOut(BaseModel):
    """Accuse de reception. Utilise par le webhook Stripe, qui doit repondre
    200 rapidement sous peine de re-livraison."""

    status: str


class HealthOut(BaseModel):
    status: str
    version: str
    environment: str
    database: str
    db_revision: str | None = None


class ConsultantFlagOut(BaseModel):
    id: int
    is_rssi_consultant: bool


class QuestionOptionOut(BaseModel):
    id: str
    text: str


class QuizQuestionOut(BaseModel):
    # UN ENTIER, pas une chaine. Declare `str`, cet endpoint a repondu 500 en
    # PRODUCTION le 2026-08-11 : aucun test ne l exercait, et la recette ne le
    # touche pas.
    id: int
    text: str
    category: str
    options: list[dict] = []


class CostCalcQuestionOut(BaseModel):
    id: int  # meme cause, meme effet que pour le quiz
    text: str
    key: str
    options: list[QuestionOptionOut] = []


class UrlScanQuotaOut(BaseModel):
    unlimited: bool
    limit: int | None = None
    used: int = 0
    remaining: int | None = None


class EnrollmentBatchOut(BaseModel):
    enrolled: int
    skipped: int
    total: int


class Nis2ReportOut(BaseModel):
    """Rapport de conformite d'une organisation de sensibilisation.

    `requirements` et `metrics` restent en structures libres : les decrire a
    moitie SUPPRIMERAIT les champs oublies, comme c'est arrive a
    `subscription_perimee` le 2026-08-11.
    """

    org_name: str
    global_score: float
    requirements: list[dict] = []
    metrics: dict = {}
    certificate_count: int = 0
    generated_at: datetime


class PublicScanRowOut(BaseModel):
    id: int
    target_url: str
    status: str
    overall_status: str | None = None
    created_at: str
    finished_at: str | None = None
    error_message: str | None = None


class AcquisitionOut(BaseModel):
    """Tableau d'acquisition. Structures libres pour la meme raison que
    ci-dessus : on type ce qu'on a lu."""

    fenetre: str | int | None = None
    jours: int | None = None
    # UN DICTIONNAIRE etape -> compte, pas une liste. Quatrieme supposition
    # fausse corrigee par le typage.
    tunnel: dict = {}
    sources: list[dict] = []
    pages: list[dict] = []
    mrr_signe_cents: int = 0
    mrr_actif_cents: int = 0
    # L interface s en sert pour distinguer « aucune donnee » d un « zero »
    # mesure : le premier appelle une explication, pas un tableau vide.
    #
    # OUBLIE D ABORD, DONC SUPPRIME DE LA REPONSE par le filtrage — meme erreur
    # que `subscription_perimee` la veille. Deux fois la meme lecture trop
    # rapide d un dictionnaire de retour.
    collecte_vide: bool = False


class OgImageOut(BaseModel):
    image_url: str | None = None


class ExtraSitesInfoOut(BaseModel):
    extra_sites: int
    pack_size: int
    pack_price_eur: float


class ModuleCompletionOut(BaseModel):
    correct: bool
    explanation: str
    correct_answer: str | int | None = None
