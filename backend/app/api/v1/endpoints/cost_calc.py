"""
Public cost calculator — 5 questions → estimated cyber-attack cost + lead capture.
No authentication required.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.core.http_cache import cache_public

router = APIRouter(prefix="/cost-calc", tags=["cost-calc"])

# ---------------------------------------------------------------------------
# Static question bank
# ---------------------------------------------------------------------------

QUESTIONS = [
    {
        "id": 1,
        "text": "Quel est l'effectif de votre organisation ?",
        "key": "size",
        "options": [
            {"id": "xs", "text": "Moins de 10 employés", "multiplier": 1.0},
            {"id": "sm", "text": "10 à 49 employés", "multiplier": 1.8},
            {"id": "md", "text": "50 à 249 employés", "multiplier": 3.5},
            {"id": "lg", "text": "250 employés et plus", "multiplier": 7.0},
        ],
    },
    {
        "id": 2,
        "text": "Quel secteur décrit le mieux votre activité ?",
        "key": "sector",
        "options": [
            {"id": "retail", "text": "Commerce / Services", "multiplier": 1.0},
            {"id": "health", "text": "Santé / Médical", "multiplier": 2.2},
            {"id": "finance", "text": "Finance / Banque", "multiplier": 3.0},
            {"id": "industry", "text": "Industrie / Fabrication", "multiplier": 1.6},
        ],
    },
    {
        "id": 3,
        "text": "Quelle est la nature des données que vous traitez ?",
        "key": "data",
        "options": [
            {"id": "public", "text": "Données publiques uniquement", "multiplier": 0.5},
            {
                "id": "internal",
                "text": "Données internes non sensibles",
                "multiplier": 1.0,
            },
            {
                "id": "personal",
                "text": "Données personnelles (clients, RH)",
                "multiplier": 2.0,
            },
            {
                "id": "critical",
                "text": "Données critiques (santé, finance)",
                "multiplier": 3.5,
            },
        ],
    },
    {
        "id": 4,
        "text": "Disposez-vous d'une solution de sauvegarde testée régulièrement ?",
        "key": "backup",
        "options": [
            {"id": "none", "text": "Non, aucune sauvegarde", "multiplier": 2.5},
            {
                "id": "partial",
                "text": "Sauvegardes partielles, non testées",
                "multiplier": 1.8,
            },
            {
                "id": "basic",
                "text": "Sauvegardes régulières, non testées",
                "multiplier": 1.2,
            },
            {
                "id": "full",
                "text": "Sauvegardes complètes et testées",
                "multiplier": 0.7,
            },
        ],
    },
    {
        "id": 5,
        "text": "Avez-vous une cyberassurance ou un plan de réponse aux incidents ?",
        "key": "coverage",
        "options": [
            {"id": "none", "text": "Non, aucune protection", "multiplier": 2.0},
            {
                "id": "partial",
                "text": "Plan basique sans cyberassurance",
                "multiplier": 1.5,
            },
            {"id": "insurance", "text": "Cyberassurance uniquement", "multiplier": 0.9},
            {"id": "full", "text": "Plan complet + cyberassurance", "multiplier": 0.5},
        ],
    },
]

BASE_COST_EUR = 25_000  # Base cost for a SME incident


def _compute_cost(answers: dict[str, str]) -> dict:
    multiplier = 1.0
    for q in QUESTIONS:
        key = q["key"]
        chosen_id = answers.get(key, q["options"][0]["id"])
        for opt in q["options"]:
            if opt["id"] == chosen_id:
                multiplier *= opt["multiplier"]
                break

    estimated = round(BASE_COST_EUR * multiplier / 1000) * 1000
    low = round(estimated * 0.6 / 1000) * 1000
    high = round(estimated * 1.8 / 1000) * 1000

    return {
        "estimated_eur": estimated,
        "low_eur": low,
        "high_eur": high,
        "multiplier": round(multiplier, 2),
        "breakdown": _breakdown(estimated),
    }


def _breakdown(total: int) -> list[dict]:
    return [
        {
            "label": "Arrêt d'activité & perte de CA",
            "pct": 35,
            "eur": round(total * 0.35),
        },
        {
            "label": "Récupération & restauration IT",
            "pct": 25,
            "eur": round(total * 0.25),
        },
        {
            "label": "Notification RGPD & juridique",
            "pct": 15,
            "eur": round(total * 0.15),
        },
        {"label": "Atteinte à la réputation", "pct": 15, "eur": round(total * 0.15)},
        {"label": "Investigation & forensics", "pct": 10, "eur": round(total * 0.10)},
    ]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CostAnswer(BaseModel):
    key: str
    option_id: str


class CostSubmit(BaseModel):
    answers: list[CostAnswer]
    email: EmailStr | None = None
    company: str | None = Field(None, max_length=255)


class CostResult(BaseModel):
    estimated_eur: int
    low_eur: int
    high_eur: int
    multiplier: float
    breakdown: list[dict]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/questions", dependencies=[Depends(cache_public(3600))])
async def get_questions():
    """Return the calculator questions (options without multiplier metadata)."""
    return [
        {
            "id": q["id"],
            "text": q["text"],
            "key": q["key"],
            "options": [{"id": o["id"], "text": o["text"]} for o in q["options"]],
        }
        for q in QUESTIONS
    ]


@router.post("/estimate", response_model=CostResult)
async def estimate_cost(payload: CostSubmit):
    """Compute cost estimate from user answers."""
    answers = {a.key: a.option_id for a in payload.answers}
    result = _compute_cost(answers)
    return CostResult(**result)
