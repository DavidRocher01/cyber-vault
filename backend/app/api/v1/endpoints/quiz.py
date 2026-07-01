"""
Public maturity quiz — 10 questions on NIS2/ISO 27001 topics.
No authentication required. Results are stored with optional email.
"""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, EmailStr, Field

from app.core.http_cache import cache_public

router = APIRouter(prefix="/quiz", tags=["quiz"])

# ---------------------------------------------------------------------------
# Static question bank (10 questions)
# ---------------------------------------------------------------------------

QUESTIONS: list[dict[str, Any]] = [
    {
        "id": 1,
        "text": "Disposez-vous d'une politique de sécurité des systèmes d'information (PSSI) formalisée ?",
        "category": "Gouvernance",
        "options": [
            {"id": "a", "text": "Non, aucune politique n'est définie"},
            {"id": "b", "text": "Partiellement — quelques règles informelles"},
            {"id": "c", "text": "Oui, mais elle n'est pas mise à jour régulièrement"},
            {"id": "d", "text": "Oui, documentée, approuvée et revue annuellement"},
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 2,
        "text": "Effectuez-vous des sauvegardes régulières de vos données critiques ?",
        "category": "Continuité",
        "options": [
            {"id": "a", "text": "Non, pas de sauvegarde en place"},
            {"id": "b", "text": "Sauvegardes manuelles occasionnelles"},
            {"id": "c", "text": "Sauvegardes automatiques, non testées"},
            {
                "id": "d",
                "text": "Sauvegardes automatiques testées et stockées hors site",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 3,
        "text": "Gérez-vous les accès à vos systèmes selon le principe du moindre privilège ?",
        "category": "Contrôle des accès",
        "options": [
            {"id": "a", "text": "Non, tous les employés ont accès à tout"},
            {"id": "b", "text": "Quelques restrictions mais sans processus formel"},
            {"id": "c", "text": "Oui, des rôles sont définis mais pas tous appliqués"},
            {
                "id": "d",
                "text": "Oui, revue régulière des accès et comptes désactivés à la sortie",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 4,
        "text": "Avez-vous un plan de réponse aux incidents de sécurité ?",
        "category": "Réponse aux incidents",
        "options": [
            {"id": "a", "text": "Non, aucun plan n'existe"},
            {
                "id": "b",
                "text": "Des contacts d'urgence existent mais pas de procédure",
            },
            {"id": "c", "text": "Un plan existe mais n'a jamais été testé"},
            {
                "id": "d",
                "text": "Plan testé, avec exercices réguliers et retours d'expérience",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 5,
        "text": "Évaluez-vous la sécurité de vos fournisseurs et sous-traitants ?",
        "category": "Chaîne d'approvisionnement",
        "options": [
            {"id": "a", "text": "Non, aucune évaluation"},
            {"id": "b", "text": "Seulement pour les contrats critiques"},
            {
                "id": "c",
                "text": "Questionnaires de sécurité envoyés aux principaux fournisseurs",
            },
            {
                "id": "d",
                "text": "Audits formels, clauses contractuelles de sécurité et suivi continu",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 6,
        "text": "Sensibilisez-vous vos collaborateurs aux risques cyber ?",
        "category": "Sensibilisation",
        "options": [
            {"id": "a", "text": "Non, aucune formation"},
            {"id": "b", "text": "Un email de sensibilisation annuel"},
            {"id": "c", "text": "Formations régulières mais pas de tests de phishing"},
            {
                "id": "d",
                "text": "Programme continu avec simulations de phishing et évaluations",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 7,
        "text": "Chiffrez-vous les données sensibles au repos et en transit ?",
        "category": "Cryptographie",
        "options": [
            {"id": "a", "text": "Non, pas de chiffrement"},
            {"id": "b", "text": "HTTPS uniquement pour le web"},
            {"id": "c", "text": "Chiffrement partiel (certains systèmes seulement)"},
            {
                "id": "d",
                "text": "Chiffrement de bout en bout et gestion des clés formalisée",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 8,
        "text": "Effectuez-vous des audits ou tests d'intrusion de vos systèmes ?",
        "category": "Tests de sécurité",
        "options": [
            {"id": "a", "text": "Jamais"},
            {"id": "b", "text": "Seulement après un incident"},
            {"id": "c", "text": "Annuellement via un prestataire externe"},
            {
                "id": "d",
                "text": "Tests réguliers (trimestriels ou continus) et Red Team",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 9,
        "text": "Surveillez-vous en continu vos journaux (logs) et alertes de sécurité ?",
        "category": "Surveillance",
        "options": [
            {"id": "a", "text": "Non, pas de collecte de logs"},
            {"id": "b", "text": "Logs stockés mais rarement consultés"},
            {"id": "c", "text": "Alertes configurées mais pas de SOC dédié"},
            {
                "id": "d",
                "text": "SIEM en place avec monitoring 24/7 et réponse automatisée",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
    {
        "id": 10,
        "text": "Appliquez-vous les mises à jour et correctifs de sécurité rapidement ?",
        "category": "Gestion des vulnérabilités",
        "options": [
            {"id": "a", "text": "Non, les mises à jour sont différées indéfiniment"},
            {
                "id": "b",
                "text": "Mises à jour réalisées manuellement de façon irrégulière",
            },
            {"id": "c", "text": "Processus de patch management mensuel"},
            {
                "id": "d",
                "text": "Correctifs critiques sous 72h, processus automatisé et suivi",
            },
        ],
        "scores": {"a": 0, "b": 1, "c": 2, "d": 3},
    },
]

MAX_SCORE = len(QUESTIONS) * 3  # 30


def _compute_level(score: int) -> dict:
    pct = round(score / MAX_SCORE * 100)
    if pct >= 80:
        return {
            "label": "Avancé",
            "color": "#4ade80",
            "description": "Votre maturité cyber est excellente. Maintenez le cap et envisagez une certification ISO 27001.",
        }
    if pct >= 60:
        return {
            "label": "Intermédiaire",
            "color": "#facc15",
            "description": "Bonne base, mais plusieurs domaines nécessitent encore du travail pour atteindre la conformité NIS2.",
        }
    if pct >= 35:
        return {
            "label": "Débutant",
            "color": "#fb923c",
            "description": "Des fondations existent mais de nombreux risques restent non couverts. Un plan d'action est recommandé.",
        }
    return {
        "label": "Insuffisant",
        "color": "#f87171",
        "description": "Votre organisation est exposée à des risques cyber significatifs. Des actions urgentes sont nécessaires.",
    }


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class QuizAnswer(BaseModel):
    question_id: int
    answer_id: str = Field(..., pattern=r"^[a-d]$")


class QuizSubmit(BaseModel):
    answers: list[QuizAnswer]
    email: EmailStr | None = None
    company: str | None = Field(None, max_length=255)


class QuizResult(BaseModel):
    score: int
    max_score: int
    percentage: int
    level: dict
    category_scores: list[dict]
    recommendations: list[str]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/questions", dependencies=[Depends(cache_public(3600))])
async def get_questions():
    """Return the list of quiz questions (without correct-answer metadata)."""
    return [
        {
            "id": q["id"],
            "text": q["text"],
            "category": q["category"],
            "options": q["options"],
        }
        for q in QUESTIONS
    ]


@router.post("/submit", response_model=QuizResult)
async def submit_quiz(payload: QuizSubmit):
    """Score a completed quiz. Optionally stores email for follow-up."""
    answers = {a.question_id: a.answer_id for a in payload.answers}

    total = 0
    cat_totals: dict[str, int] = {}
    cat_max: dict[str, int] = {}

    for q in QUESTIONS:
        chosen = answers.get(q["id"], "a")
        pts = q["scores"].get(chosen, 0)
        total += pts
        cat = q["category"]
        cat_totals[cat] = cat_totals.get(cat, 0) + pts
        cat_max[cat] = cat_max.get(cat, 0) + 3

    category_scores = [
        {
            "category": cat,
            "score": cat_totals[cat],
            "max": cat_max[cat],
            "percentage": round(cat_totals[cat] / cat_max[cat] * 100),
        }
        for cat in cat_totals
    ]

    weakest = sorted(category_scores, key=lambda c: c["percentage"])[:3]
    recommendations = [
        f"Renforcez le domaine **{c['category']}** (score {c['percentage']}%) — priorité {'haute' if c['percentage'] < 34 else 'moyenne'}."
        for c in weakest
    ]

    return QuizResult(
        score=total,
        max_score=MAX_SCORE,
        percentage=round(total / MAX_SCORE * 100),
        level=_compute_level(total),
        category_scores=category_scores,
        recommendations=recommendations,
    )
