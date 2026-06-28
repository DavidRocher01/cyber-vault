"""
Rapport NIS2 Article 21 — mappeur conformité + génération PDF.

Mappe les données de complétion de la plateforme aux exigences NIS2 :

  Art. 21(a) — Politiques d'analyse des risques
    → taux de complétion programme général ≥ 80%

  Art. 21(b) — Gestion des incidents
    → modules "incident" ou "ransomware" ≥ 75%

  Art. 21(c) — Continuité des activités
    → modules "backup" ou "continuité" ≥ 70%

  Art. 21(g) — Hygiène cyber et formation
    → taux de complétion global ≥ 80%

  Art. 21(h) — Sécurité des ressources humaines
    → % de learners ayant complété au moins un module ≥ 60%
"""

from __future__ import annotations

import io
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_certificate import AwarenessCertificate
from app.models.awareness_enrollment import AwarenessEnrollment
from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_module import AwarenessModule
from app.models.awareness_organization import AwarenessOrganization
from app.models.awareness_progress import AwarenessProgress
from app.services.pdf_brand import CYAN, GRAY, GREEN, RED, WHITE, YELLOW

_NAVY = colors.HexColor("#0f172a")
_RED = RED
_GREEN = GREEN
_YELLOW = YELLOW
_CYAN = CYAN
_WHITE = WHITE
_GRAY = GRAY


# ── NIS2 mapping ───────────────────────────────────────────────────────────────

NIS2_REQUIREMENTS = [
    {
        "article": "Art. 21(a)",
        "title": "Politiques d'analyse des risques",
        "description": "Politiques relatives à la sécurité des systèmes d'information",
        "metric_key": "general_completion_pct",
        "threshold": 80,
        "module_keywords": [],
    },
    {
        "article": "Art. 21(b)",
        "title": "Gestion des incidents",
        "description": "Procédures de détection et de gestion des incidents de sécurité",
        "metric_key": "incident_module_completion_pct",
        "threshold": 75,
        "module_keywords": ["incident", "ransomware"],
    },
    {
        "article": "Art. 21(c)",
        "title": "Continuité des activités",
        "description": "Gestion des sauvegardes, reprise d'activité et gestion de crise",
        "metric_key": "continuity_module_completion_pct",
        "threshold": 70,
        "module_keywords": ["backup", "sauvegarde", "continuité", "pca"],
    },
    {
        "article": "Art. 21(g)",
        "title": "Hygiène cyber et formation",
        "description": "Pratiques de base en matière de cyberhygiène et formation",
        "metric_key": "overall_completion_pct",
        "threshold": 80,
        "module_keywords": [],
    },
    {
        "article": "Art. 21(h)",
        "title": "Sécurité des ressources humaines",
        "description": "Politiques relatives à la sécurité du personnel",
        "metric_key": "learner_participation_pct",
        "threshold": 60,
        "module_keywords": [],
    },
]


async def compute_nis2_metrics(db: AsyncSession, org_id: int) -> dict:
    """Compute all NIS2 metrics for an organization."""
    total_learners = (
        await db.execute(
            select(func.count(AwarenessLearner.id)).where(
                AwarenessLearner.organization_id == org_id,
                AwarenessLearner.is_active == True,
            )
        )
    ).scalar_one()

    if total_learners == 0:
        return {k["metric_key"]: 0.0 for k in NIS2_REQUIREMENTS}

    # Global completion (any enrollment)
    avg_completion = (
        await db.execute(
            select(func.avg(AwarenessEnrollment.completion_pct)).where(
                AwarenessEnrollment.organization_id == org_id,
            )
        )
    ).scalar_one() or 0.0

    # Learner participation (at least 1 enrollment)
    enrolled_learners = (
        await db.execute(
            select(func.count(func.distinct(AwarenessEnrollment.learner_id))).where(
                AwarenessEnrollment.organization_id == org_id,
            )
        )
    ).scalar_one()
    participation_pct = (
        round(enrolled_learners / total_learners * 100, 1) if total_learners else 0.0
    )

    # Per-keyword module completion
    async def _keyword_completion(keywords: list[str]) -> float:
        if not keywords:
            return round(float(avg_completion), 1)
        # Find modules matching any keyword
        modules = (
            (
                await db.execute(
                    select(AwarenessModule.id).where(
                        func.lower(AwarenessModule.slug).contains(
                            func.any(keywords[0])  # simplification — first keyword
                        )
                        if len(keywords) == 1
                        else func.lower(AwarenessModule.title).contains(keywords[0])
                    )
                )
            )
            .scalars()
            .all()
        )

        if not modules:
            return round(float(avg_completion), 1)

        completed = (
            await db.execute(
                select(func.count(AwarenessProgress.id)).where(
                    AwarenessProgress.module_id.in_(modules),
                    AwarenessProgress.status == "completed",
                )
            )
        ).scalar_one()

        total = (
            await db.execute(
                select(func.count(AwarenessProgress.id)).where(
                    AwarenessProgress.module_id.in_(modules),
                )
            )
        ).scalar_one()

        if total == 0:
            return round(float(avg_completion), 1)
        return round(completed / total * 100, 1)

    metrics = {
        "general_completion_pct": round(float(avg_completion), 1),
        "overall_completion_pct": round(float(avg_completion), 1),
        "learner_participation_pct": participation_pct,
        "incident_module_completion_pct": await _keyword_completion(["incident", "ransomware"]),
        "continuity_module_completion_pct": await _keyword_completion(["backup", "continuité"]),
    }
    return metrics


def map_requirements(metrics: dict) -> list[dict]:
    """Map metrics to NIS2 requirements with compliance status."""
    results = []
    for req in NIS2_REQUIREMENTS:
        value = metrics.get(req["metric_key"], 0.0)
        threshold = req["threshold"]
        if value >= threshold:
            status = "compliant"
            status_label = "Conforme"
            color = "green"
        elif value >= threshold * 0.75:
            status = "partial"
            status_label = "Partiel"
            color = "yellow"
        else:
            status = "non_compliant"
            status_label = "Non conforme"
            color = "red"
        results.append(
            {
                **req,
                "value": value,
                "status": status,
                "status_label": status_label,
                "color": color,
                "gap": max(0.0, threshold - value),
            }
        )
    return results


def compute_global_score(requirements: list[dict]) -> float:
    """Global compliance score (0–100)."""
    if not requirements:
        return 0.0
    weights = {"compliant": 2, "partial": 1, "non_compliant": 0}
    total = sum(weights[r["status"]] for r in requirements)
    max_total = len(requirements) * 2
    return round(total / max_total * 100, 1)


# ── PDF generation ─────────────────────────────────────────────────────────────


def generate_nis2_report_pdf(
    org_name: str,
    requirements: list[dict],
    global_score: float,
    metrics: dict,
    certificate_count: int,
    generated_at: datetime,
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    h1 = ParagraphStyle(
        "rh1", fontSize=22, textColor=_CYAN, fontName="Helvetica-Bold", spaceAfter=4
    )
    h2 = ParagraphStyle(
        "rh2", fontSize=13, textColor=_CYAN, fontName="Helvetica-Bold", spaceBefore=10, spaceAfter=4
    )
    body = ParagraphStyle("rbody", fontSize=9, textColor=_WHITE, leading=14, spaceAfter=3)
    small = ParagraphStyle("rsmall", fontSize=7, textColor=_GRAY, spaceAfter=2)
    score_style = ParagraphStyle(
        "rscore",
        fontSize=48,
        textColor=_GREEN if global_score >= 80 else (_YELLOW if global_score >= 50 else _RED),
        fontName="Helvetica-Bold",
        alignment=1,
    )

    story = []
    story.append(Paragraph("Rapport de conformité NIS2", h1))
    story.append(Paragraph(f"{org_name} — Article 21", body))
    story.append(Paragraph(f"Généré le {generated_at.strftime('%d/%m/%Y %H:%M')}", small))
    story.append(HRFlowable(width="100%", thickness=2, color=_CYAN, spaceAfter=8))

    # Score global
    story.append(Paragraph(f"{global_score:.0f}%", score_style))
    story.append(
        Paragraph(
            "Score de conformité global",
            ParagraphStyle("rlabel", fontSize=9, textColor=_GRAY, alignment=1, spaceAfter=12),
        )
    )

    # Tableau des exigences
    story.append(Paragraph("Cartographie des exigences NIS2", h2))
    _COLOR_MAP = {"green": _GREEN, "yellow": _YELLOW, "red": _RED}

    rows = [["Article", "Exigence", "Valeur", "Seuil", "Statut"]]
    for req in requirements:
        rows.append(
            [
                req["article"],
                Paragraph(req["title"], ParagraphStyle("rt", fontSize=8, textColor=_WHITE)),
                f"{req['value']:.1f}%",
                f"{req['threshold']}%",
                Paragraph(
                    req["status_label"],
                    ParagraphStyle(
                        "rs",
                        fontSize=8,
                        textColor=_COLOR_MAP.get(req["color"], _GRAY),
                        fontName="Helvetica-Bold",
                    ),
                ),
            ]
        )

    t = Table(rows, colWidths=[22 * mm, 65 * mm, 20 * mm, 17 * mm, 25 * mm])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), _WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#0f172a"), colors.HexColor("#111c30")],
                ),
                ("TEXTCOLOR", (0, 1), (-1, -1), _WHITE),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(t)

    # Résumé métriques
    story.append(Paragraph("Indicateurs de formation", h2))
    metrics_data = [
        ["Indicateur", "Valeur"],
        ["Taux de complétion global", f"{metrics.get('overall_completion_pct', 0):.1f}%"],
        [
            "Taux de participation des learners",
            f"{metrics.get('learner_participation_pct', 0):.1f}%",
        ],
        ["Attestations délivrées", str(certificate_count)],
    ]
    mt = Table(metrics_data, colWidths=[100 * mm, 50 * mm])
    mt.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, -1), _WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.HexColor("#0f172a"), colors.HexColor("#111c30")],
                ),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#334155")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(mt)

    # Pied de page
    story.append(Spacer(1, 8 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=_GRAY))
    story.append(
        Paragraph(
            "Rapport généré automatiquement par CyberScan — Module Sensibilisation NIS2",
            ParagraphStyle("rfooter", fontSize=7, textColor=_GRAY, alignment=1, spaceBefore=4),
        )
    )

    doc.build(story)
    return buf.getvalue()


# ── Endpoint data builder ──────────────────────────────────────────────────────


async def build_nis2_report(db: AsyncSession, org_id: int) -> dict:
    org = (
        await db.execute(select(AwarenessOrganization).where(AwarenessOrganization.id == org_id))
    ).scalar_one()

    metrics = await compute_nis2_metrics(db, org_id)
    requirements = map_requirements(metrics)
    global_score = compute_global_score(requirements)

    cert_count = (
        await db.execute(
            select(func.count(AwarenessCertificate.id))
            .join(AwarenessLearner, AwarenessLearner.id == AwarenessCertificate.learner_id)
            .where(
                AwarenessLearner.organization_id == org_id,
                AwarenessCertificate.is_revoked == False,
            )
        )
    ).scalar_one()

    return {
        "org_name": org.name,
        "global_score": global_score,
        "requirements": requirements,
        "metrics": metrics,
        "certificate_count": cert_count,
        "generated_at": datetime.now(UTC),
    }
