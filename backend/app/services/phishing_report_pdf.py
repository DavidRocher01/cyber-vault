"""
Generate a PDF report for a completed phishing simulation campaign.
Uses ReportLab (already in requirements).
"""

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.phishing import PhishingCampaign, PhishingTarget

_DARK = colors.HexColor("#0f172a")
_CYAN = colors.HexColor("#06b6d4")
_RED = colors.HexColor("#ef4444")
_YELLOW = colors.HexColor("#eab308")
_GREEN = colors.HexColor("#22c55e")
_GRAY = colors.HexColor("#94a3b8")
_LIGHT_BG = colors.HexColor("#f8fafc")

_PAGE_W, _PAGE_H = A4


def _risk_color(rate: float) -> colors.Color:
    if rate >= 0.30:
        return _RED
    if rate >= 0.15:
        return _YELLOW
    return _GREEN


def _risk_label(rate: float) -> str:
    if rate >= 0.30:
        return "ÉLEVÉ"
    if rate >= 0.15:
        return "MOYEN"
    return "FAIBLE"


def generate_phishing_report(
    campaign: PhishingCampaign,
    targets: list[PhishingTarget],
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=_DARK,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        fontName="Helvetica",
        fontSize=12,
        textColor=_GRAY,
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=_DARK,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body",
        fontName="Helvetica",
        fontSize=10,
        textColor=_DARK,
        spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "Small",
        fontName="Helvetica",
        fontSize=8,
        textColor=_GRAY,
    )

    # Compute stats
    n = campaign.targets_count or len(targets) or 1
    click_rate = campaign.clicked_count / n
    open_rate = campaign.opened_count / n
    submit_rate = campaign.submitted_count / n

    # Department breakdown
    dept_stats: dict[str, dict[str, int]] = {}
    for t in targets:
        dept = t.department or "Non renseigné"
        if dept not in dept_stats:
            dept_stats[dept] = {"total": 0, "clicked": 0, "submitted": 0}
        dept_stats[dept]["total"] += 1
        if t.status in ("clicked", "submitted"):
            dept_stats[dept]["clicked"] += 1
        if t.status == "submitted":
            dept_stats[dept]["submitted"] += 1

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("CyberScan", ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=11, textColor=_CYAN)))
    story.append(Paragraph("Rapport de simulation de phishing", title_style))
    story.append(Paragraph(campaign.name, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=_CYAN, spaceAfter=10))

    # ── Campaign meta ────────────────────────────────────────────────────────
    generated_at = datetime.now(timezone.utc).strftime("%d/%m/%Y à %H:%M UTC")
    finished = campaign.finished_at.strftime("%d/%m/%Y") if campaign.finished_at else "En cours"
    started = campaign.started_at.strftime("%d/%m/%Y") if campaign.started_at else "—"
    meta_data = [
        ["Campagne", campaign.name],
        ["Domaine ciblé", campaign.domain or "—"],
        ["Date de lancement", started],
        ["Date de fin", finished],
        ["Nombre de cibles", str(campaign.targets_count)],
        ["Plan", campaign.plan_tier.capitalize()],
        ["Rapport généré", generated_at],
    ]
    meta_table = Table(meta_data, colWidths=[50 * mm, None])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), _GRAY),
        ("TEXTCOLOR", (1, 0), (1, -1), _DARK),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_LIGHT_BG, colors.white]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    # ── Summary stats ────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé des résultats", section_style))

    stats_data = [
        ["Indicateur", "Nombre", "Taux", "Risque"],
        ["Emails envoyés", str(campaign.emails_sent), "—", "—"],
        ["Emails ouverts", str(campaign.opened_count), f"{open_rate:.0%}", "—"],
        ["Liens cliqués", str(campaign.clicked_count), f"{click_rate:.0%}", _risk_label(click_rate)],
        ["Données soumises", str(campaign.submitted_count), f"{submit_rate:.0%}", _risk_label(submit_rate)],
    ]
    stats_table = Table(stats_data, colWidths=[65 * mm, 30 * mm, 30 * mm, 40 * mm])
    risk_click_color = _risk_color(click_rate)
    stats_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _DARK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("TEXTCOLOR", (3, 3), (3, 3), risk_click_color),
        ("FONTNAME", (3, 3), (3, 3), "Helvetica-Bold"),
    ]))
    story.append(stats_table)
    story.append(Spacer(1, 6 * mm))

    # ── Risk score ───────────────────────────────────────────────────────────
    rc = _risk_color(click_rate)
    rl = _risk_label(click_rate)
    story.append(Paragraph(
        f"Score de risque global : <font color='#{rc.hexval()[2:]}'><b>{rl}</b></font> "
        f"(taux de clic : {click_rate:.0%})",
        body_style,
    ))
    story.append(Spacer(1, 4 * mm))

    # ── Department breakdown ─────────────────────────────────────────────────
    if len(dept_stats) > 1:
        story.append(Paragraph("Analyse par département", section_style))
        dept_header = [["Département", "Cibles", "Clics", "Taux de clic"]]
        dept_rows = [
            [
                dept,
                str(s["total"]),
                str(s["clicked"]),
                f"{s['clicked'] / s['total']:.0%}" if s["total"] else "—",
            ]
            for dept, s in sorted(dept_stats.items(), key=lambda x: x[1]["clicked"] / (x[1]["total"] or 1), reverse=True)
        ]
        dept_table = Table(dept_header + dept_rows, colWidths=[75 * mm, 30 * mm, 30 * mm, 40 * mm])
        dept_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), _DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(dept_table)
        story.append(Spacer(1, 6 * mm))

    # ── Recommendations ──────────────────────────────────────────────────────
    story.append(Paragraph("Recommandations", section_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=6))

    recs = _get_recommendations(click_rate, submit_rate)
    for i, rec in enumerate(recs, 1):
        story.append(Paragraph(f"{i}. {rec}", body_style))

    story.append(Spacer(1, 6 * mm))

    # ── Legal disclaimer ─────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=4))
    story.append(Paragraph(
        "Ce rapport est confidentiel et destiné exclusivement à l'entreprise cliente. "
        "La simulation a été réalisée dans le cadre d'une convention d'exercice signée entre les parties. "
        "Aucune donnée personnelle réelle n'a été collectée. — CyberScan",
        small_style,
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _get_recommendations(click_rate: float, submit_rate: float) -> list[str]:
    recs = [
        "Organiser une session de sensibilisation collective sur la reconnaissance du phishing "
        "(durée recommandée : 45 min, format atelier interactif).",
        "Mettre en place un processus de signalement simplifié (bouton 'Signaler un email suspect' "
        "dans le client de messagerie) pour encourager la remontée des tentatives.",
        "Activer l'authentification multi-facteurs (MFA) sur l'ensemble des comptes email et outils SaaS "
        "pour limiter l'impact d'une compromission d'identifiants.",
    ]
    if click_rate >= 0.30:
        recs.insert(0,
            "⚠️ Taux de clic élevé (≥ 30 %) : une formation ciblée en urgence est recommandée "
            "pour les populations les plus exposées identifiées dans ce rapport."
        )
    if submit_rate >= 0.10:
        recs.append(
            "⚠️ Taux de soumission de données significatif : vérifier si des mots de passe réels "
            "ont été utilisés et procéder à une rotation préventive des comptes concernés."
        )
    recs.append(
        "Planifier une nouvelle campagne de simulation dans 3 mois pour mesurer l'amélioration "
        "après les actions de formation."
    )
    return recs
