"""
Generate a PDF report for a completed phishing simulation campaign.
Uses ReportLab (already in requirements).
"""

import io
import json
from datetime import UTC, datetime

from loguru import logger
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

from app.models.phishing import PhishingCampaign, PhishingTarget

_DARK = colors.HexColor("#0f172a")
_CYAN = colors.HexColor("#06b6d4")
_RED = colors.HexColor("#ef4444")
_YELLOW = colors.HexColor("#eab308")
_GREEN = colors.HexColor("#22c55e")
_GRAY = colors.HexColor("#94a3b8")
_LIGHT_BG = colors.HexColor("#f8fafc")
_PAGE_W, _PAGE_H = A4

_SCENARIO_LABELS: dict[str, str] = {
    "ceo-fraud": "Fraude au Président",
    "o365-credentials": "Credentials Microsoft 365",
    "fake-invoice": "Fausse relance comptable",
    "bank-alert": "Fausse alerte bancaire",
    "parcel-delivery": "Faux avis de livraison",
    "it-helpdesk": "Faux email DSI / Helpdesk",
    "hr-notification": "Fausse notification RH",
    "docusign": "Fausse demande DocuSign",
    "vpn-alert": "Fausse alerte sécurité VPN",
    "hr-document": "Document RH confidentiel",
    "teams-notification": "Notification Microsoft Teams",
    "sharepoint-share": "Partage SharePoint",
    "it-ticket": "Ticket Helpdesk DSI",
}


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


def _global_risk(click_rate: float, submit_rate: float) -> tuple[str, colors.Color]:
    """Combined risk: submission weighs double."""
    score = click_rate + submit_rate * 2
    if score >= 0.50 or submit_rate >= 0.20:
        return "ÉLEVÉ", _RED
    if score >= 0.20 or submit_rate >= 0.08:
        return "MOYEN", _YELLOW
    return "FAIBLE", _GREEN


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(_GRAY)
    page_num = f"Page {doc.page}"
    canvas.drawRightString(_PAGE_W - 20 * mm, 12 * mm, page_num)
    canvas.drawString(20 * mm, 12 * mm, "Rocher Cybersécurité — Rapport confidentiel")
    canvas.restoreState()


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
        bottomMargin=22 * mm,
    )

    title_style = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=_DARK,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle", fontName="Helvetica", fontSize=12, textColor=_GRAY, spaceAfter=10
    )
    section_style = ParagraphStyle(
        "Section",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=_DARK,
        spaceBefore=14,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "Body", fontName="Helvetica", fontSize=10, textColor=_DARK, spaceAfter=4
    )
    small_style = ParagraphStyle("Small", fontName="Helvetica", fontSize=8, textColor=_GRAY)
    brand_style = ParagraphStyle("Brand", fontName="Helvetica-Bold", fontSize=11, textColor=_CYAN)

    # ── Compute stats ────────────────────────────────────────────────────────
    n = campaign.targets_count or len(targets) or 1
    click_rate = campaign.clicked_count / n
    open_rate = campaign.opened_count / n
    submit_rate = campaign.submitted_count / n

    global_risk_label, global_risk_color = _global_risk(click_rate, submit_rate)

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

    # Per-scenario breakdown (uses target.scenario_key set during send)
    scenario_perf: dict[str, dict[str, int]] = {}
    for t in targets:
        key = t.scenario_key or "__unknown__"
        if key not in scenario_perf:
            scenario_perf[key] = {"total": 0, "opened": 0, "clicked": 0, "submitted": 0}
        scenario_perf[key]["total"] += 1
        if t.status in ("opened", "clicked", "submitted", "reported"):
            scenario_perf[key]["opened"] += 1
        if t.status in ("clicked", "submitted"):
            scenario_perf[key]["clicked"] += 1
        if t.status == "submitted":
            scenario_perf[key]["submitted"] += 1
    # Only keep if we have meaningful per-scenario data (at least one key set)
    has_scenario_perf = any(k != "__unknown__" for k in scenario_perf)

    # Compromised targets (submitted credentials)
    compromised = [t for t in targets if t.status == "submitted"]

    # Scenario keys used
    scenario_keys: list[str] = []
    try:
        scenario_keys = json.loads(campaign.scenario_keys or "[]")
    except json.JSONDecodeError as exc:
        logger.warning("scenario_keys illisible (JSON) pour la campagne, liste vide : {}", exc)

    # Median time-to-click (hours)
    click_delays_h: list[float] = []
    for t in targets:
        if t.clicked_at and t.email_sent_at:
            click_delays_h.append((t.clicked_at - t.email_sent_at).total_seconds() / 3600)
    median_click_str: str | None = None
    if click_delays_h:
        sorted_d = sorted(click_delays_h)
        mh = sorted_d[len(sorted_d) // 2]
        median_click_str = f"{int(mh)}h{int((mh % 1) * 60):02d}min"

    story = []

    # ── Header ──────────────────────────────────────────────────────────────
    story.append(Paragraph("Rocher Cybersécurité", brand_style))
    story.append(Paragraph("Rapport de simulation de phishing", title_style))
    story.append(Paragraph(campaign.name, subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=_CYAN, spaceAfter=10))

    # ── Campaign meta ────────────────────────────────────────────────────────
    generated_at = datetime.now(UTC).strftime("%d/%m/%Y à %H:%M UTC")
    started = campaign.started_at.strftime("%d/%m/%Y") if campaign.started_at else "—"
    finished = campaign.finished_at.strftime("%d/%m/%Y") if campaign.finished_at else "En cours"
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
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), _GRAY),
                ("TEXTCOLOR", (1, 0), (1, -1), _DARK),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [_LIGHT_BG, colors.white]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8 * mm))

    # ── Summary stats ────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé des résultats", section_style))
    stats_data = [
        ["Indicateur", "Nombre", "Taux", "Risque"],
        ["Emails envoyés", str(campaign.emails_sent), "—", "—"],
        ["Emails ouverts", str(campaign.opened_count), f"{open_rate:.0%}", "—"],
        [
            "Liens cliqués",
            str(campaign.clicked_count),
            f"{click_rate:.0%}",
            _risk_label(click_rate),
        ],
        [
            "Données soumises",
            str(campaign.submitted_count),
            f"{submit_rate:.0%}",
            _risk_label(submit_rate),
        ],
    ]
    if median_click_str:
        stats_data.append(["Délai médian avant clic", median_click_str, "—", "—"])
    stats_table = Table(stats_data, colWidths=[65 * mm, 30 * mm, 30 * mm, 40 * mm])
    stats_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("TEXTCOLOR", (3, 3), (3, 3), _risk_color(click_rate)),
                ("FONTNAME", (3, 3), (3, 3), "Helvetica-Bold"),
                ("TEXTCOLOR", (3, 4), (3, 4), _risk_color(submit_rate)),
                ("FONTNAME", (3, 4), (3, 4), "Helvetica-Bold"),
            ]
        )
    )
    story.append(stats_table)
    story.append(Spacer(1, 5 * mm))

    # ── Global risk score ────────────────────────────────────────────────────
    hex_color = global_risk_color.hexval()[2:]
    story.append(
        Paragraph(
            f"Niveau de risque global : <font color='#{hex_color}'><b>{global_risk_label}</b></font> "
            f"— clic : {click_rate:.0%} | soumission : {submit_rate:.0%}",
            body_style,
        )
    )
    story.append(Spacer(1, 6 * mm))

    # ── Per-scenario performance ─────────────────────────────────────────────
    if has_scenario_perf and len(scenario_perf) > 1:
        story.append(Paragraph("Performance par scénario", section_style))
        sc_perf_rows = [
            [
                "Scénario",
                "Cibles",
                "Ouvert.",
                "Taux ouv.",
                "Clics",
                "Taux clic",
                "Soum.",
            ]
        ]
        for key, s in sorted(
            scenario_perf.items(),
            key=lambda x: x[1]["clicked"] / (x[1]["total"] or 1),
            reverse=True,
        ):
            if key == "__unknown__":
                continue
            cr = s["clicked"] / (s["total"] or 1)
            orr = s["opened"] / (s["total"] or 1)
            sc_perf_rows.append(
                [
                    _SCENARIO_LABELS.get(key, key),
                    str(s["total"]),
                    str(s["opened"]),
                    f"{orr:.0%}",
                    str(s["clicked"]),
                    f"{cr:.0%}",
                    str(s["submitted"]),
                ]
            )
        sc_perf_table = Table(
            sc_perf_rows,
            colWidths=[52 * mm, 15 * mm, 17 * mm, 17 * mm, 15 * mm, 17 * mm, 17 * mm],
        )
        sc_perf_style = [
            ("BACKGROUND", (0, 0), (-1, 0), _DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        # Highlight high-risk rows in the click rate column
        for row_i, (key, s) in enumerate(
            sorted(
                scenario_perf.items(),
                key=lambda x: x[1]["clicked"] / (x[1]["total"] or 1),
                reverse=True,
            ),
            start=1,
        ):
            if key == "__unknown__":
                continue
            cr = s["clicked"] / (s["total"] or 1)
            if cr >= 0.30:
                sc_perf_style.append(("TEXTCOLOR", (5, row_i), (5, row_i), _RED))
                sc_perf_style.append(("FONTNAME", (5, row_i), (5, row_i), "Helvetica-Bold"))
            elif cr >= 0.15:
                sc_perf_style.append(("TEXTCOLOR", (5, row_i), (5, row_i), _YELLOW))
                sc_perf_style.append(("FONTNAME", (5, row_i), (5, row_i), "Helvetica-Bold"))
        sc_perf_table.setStyle(TableStyle(sc_perf_style))
        story.append(sc_perf_table)
        story.append(Spacer(1, 6 * mm))

    # ── Scenarios used ───────────────────────────────────────────────────────
    if scenario_keys:
        story.append(Paragraph("Scénarios déployés", section_style))
        scenario_rows = [["#", "Clé", "Scénario"]]
        for i, key in enumerate(scenario_keys, 1):
            scenario_rows.append(
                [
                    str(i),
                    key,
                    _SCENARIO_LABELS.get(key, key),
                ]
            )
        sc_table = Table(scenario_rows, colWidths=[8 * mm, 50 * mm, None])
        sc_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(sc_table)
        story.append(Spacer(1, 6 * mm))

    # ── Department breakdown ─────────────────────────────────────────────────
    if len(dept_stats) > 1:
        story.append(Paragraph("Analyse par département", section_style))
        dept_header = [["Département", "Cibles", "Clics", "Taux de clic", "Soumissions"]]
        dept_rows = [
            [
                dept,
                str(s["total"]),
                str(s["clicked"]),
                f"{s['clicked'] / s['total']:.0%}" if s["total"] else "—",
                str(s["submitted"]),
            ]
            for dept, s in sorted(
                dept_stats.items(),
                key=lambda x: x[1]["clicked"] / (x[1]["total"] or 1),
                reverse=True,
            )
        ]
        dept_table = Table(
            dept_header + dept_rows,
            colWidths=[60 * mm, 22 * mm, 22 * mm, 35 * mm, 30 * mm],
        )
        dept_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _DARK),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(dept_table)
        story.append(Spacer(1, 6 * mm))

    # ── Compromised targets ──────────────────────────────────────────────────
    if compromised:
        story.append(
            Paragraph(
                f"Comptes compromis ({len(compromised)} cible{'s' if len(compromised) > 1 else ''})",
                section_style,
            )
        )
        story.append(
            Paragraph(
                "Les personnes suivantes ont soumis leurs identifiants sur la page de phishing. "
                "Une action de sensibilisation individuelle est recommandée.",
                body_style,
            )
        )
        comp_header = [["Email", "Prénom", "Nom", "Département"]]
        comp_rows = [
            [
                t.email,
                t.first_name or "—",
                t.last_name or "—",
                t.department or "—",
            ]
            for t in compromised
        ]
        comp_table = Table(comp_header + comp_rows, colWidths=[65 * mm, 30 * mm, 30 * mm, None])
        comp_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), _RED),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.HexColor("#fff5f5"), colors.white],
                    ),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fecaca")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(comp_table)
        story.append(Spacer(1, 6 * mm))

    # ── Full targets table ───────────────────────────────────────────────────
    if targets:
        story.append(Paragraph(f"Résultats détaillés par cible ({len(targets)})", section_style))
        _STATUS_LABELS = {
            "pending": "En attente",
            "email_sent": "Envoyé",
            "opened": "Ouvert",
            "clicked": "Cliqué",
            "submitted": "Identifiants saisis",
            "reported": "Signalé",
        }
        _STATUS_COLORS = {
            "submitted": _RED,
            "clicked": colors.HexColor("#f97316"),
            "opened": _YELLOW,
            "reported": _GREEN,
        }
        tgt_header = [["Email", "Prénom", "Département", "Scénario", "Statut"]]
        tgt_rows = []
        for t in sorted(
            targets,
            key=lambda x: (
                {
                    "submitted": 0,
                    "clicked": 1,
                    "opened": 2,
                    "email_sent": 3,
                    "reported": 4,
                    "pending": 5,
                }.get(x.status, 5)
            ),
        ):
            tgt_rows.append(
                [
                    t.email,
                    t.first_name or "—",
                    t.department or "—",
                    _SCENARIO_LABELS.get(t.scenario_key or "", t.scenario_key or "—"),
                    _STATUS_LABELS.get(t.status, t.status),
                ]
            )
        tgt_table = Table(
            tgt_header + tgt_rows,
            colWidths=[65 * mm, 25 * mm, 30 * mm, 30 * mm, 20 * mm],
        )
        tgt_style = [
            ("BACKGROUND", (0, 0), (-1, 0), _DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT_BG, colors.white]),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
        for row_i, t in enumerate(
            sorted(
                targets,
                key=lambda x: (
                    {
                        "submitted": 0,
                        "clicked": 1,
                        "opened": 2,
                        "email_sent": 3,
                        "reported": 4,
                        "pending": 5,
                    }.get(x.status, 5)
                ),
            ),
            start=1,
        ):
            c = _STATUS_COLORS.get(t.status)
            if c:
                tgt_style.append(("TEXTCOLOR", (4, row_i), (4, row_i), c))
                tgt_style.append(("FONTNAME", (4, row_i), (4, row_i), "Helvetica-Bold"))
        tgt_table.setStyle(TableStyle(tgt_style))
        story.append(tgt_table)
        story.append(Spacer(1, 6 * mm))

    # ── Recommendations ──────────────────────────────────────────────────────
    story.append(Paragraph("Recommandations", section_style))
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=6)
    )
    for i, rec in enumerate(_get_recommendations(click_rate, submit_rate), 1):
        story.append(Paragraph(f"{i}. {rec}", body_style))
    story.append(Spacer(1, 6 * mm))

    # ── Legal disclaimer ─────────────────────────────────────────────────────
    story.append(
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#e2e8f0"), spaceAfter=4)
    )
    story.append(
        Paragraph(
            "Ce rapport est confidentiel et destiné exclusivement à l'entreprise cliente. "
            "La simulation a été réalisée dans le cadre d'une convention d'exercice signée entre les parties. "
            "Aucune donnée personnelle réelle n'a été collectée ni stockée. — Rocher Cybersécurité",
            small_style,
        )
    )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


def _get_recommendations(click_rate: float, submit_rate: float) -> list[str]:
    recs = []
    if click_rate >= 0.30:
        recs.append(
            "⚠️ Taux de clic élevé (≥ 30 %) : une formation ciblée en urgence est recommandée "
            "pour les populations les plus exposées identifiées dans ce rapport."
        )
    if submit_rate >= 0.10:
        recs.append(
            "⚠️ Des identifiants ont été soumis sur la page de phishing : vérifier si des mots de passe "
            "réels ont pu être utilisés et procéder à une rotation préventive des comptes concernés."
        )
    recs += [
        "Organiser une session de sensibilisation collective sur la reconnaissance du phishing "
        "(durée recommandée : 45 min, format atelier interactif).",
        "Mettre en place un processus de signalement simplifié (bouton « Signaler un email suspect » "
        "dans le client de messagerie) pour encourager la remontée des tentatives.",
        "Activer l'authentification multi-facteurs (MFA) sur l'ensemble des comptes email et outils SaaS "
        "pour limiter l'impact d'une compromission d'identifiants.",
        "Planifier une nouvelle simulation dans 3 mois pour mesurer l'amélioration après les actions de formation.",
    ]
    return recs
