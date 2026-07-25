"""cover.py — cover page, table of contents and executive summary builders."""

from __future__ import annotations

from typing import Any

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .theme import (
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_WHITE,
    _section_header,
    _status_color,
    _status_inline,
    _std_table_style,
)


def _build_cover(
    target_url: str,
    report_date: str,
    styles: dict[str, Any],
    page_w: float,
    page_h: float,
    overall_status: str = "OK",
) -> list:
    story = []

    col_w = page_w

    # ── Logo zone ────────────────────────────────────────────────────────────
    cs_badge_style = ParagraphStyle(
        "cs_badge",
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=COLOR_WHITE,
        alignment=TA_CENTER,
    )
    cs_label_style = ParagraphStyle(
        "cs_label",
        fontName="Helvetica-Bold",
        fontSize=26,
        textColor=COLOR_TEXT,
        alignment=TA_CENTER,
    )
    cs_sub_style = ParagraphStyle(
        "cs_sub",
        fontName="Helvetica",
        fontSize=13,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
    )

    logo_badge_data = [[Paragraph("CS", cs_badge_style)]]
    logo_badge = Table(logo_badge_data, colWidths=[1.8 * cm], rowHeights=[1.8 * cm])
    logo_badge.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROUNDEDCORNERS", [6]),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    logo_row = Table(
        [[logo_badge, Paragraph("Rocher Cybersécurité", cs_label_style)]],
        colWidths=[2 * cm, col_w - 2 * cm],
    )
    logo_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    story.append(Spacer(1, 2 * cm))
    story.append(logo_row)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Rapport d'Audit de Sécurité", cs_sub_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=0)
    )
    story.append(Spacer(1, 0.6 * cm))

    # ── Cible block ──────────────────────────────────────────────────────────
    label_style = ParagraphStyle(
        "cov_label",
        fontName="Helvetica",
        fontSize=9,
        textColor=COLOR_MUTED,
    )
    url_style = ParagraphStyle(
        "cov_url",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=COLOR_PRIMARY,
    )
    date_style = ParagraphStyle(
        "cov_date",
        fontName="Helvetica",
        fontSize=12,
        textColor=COLOR_TEXT,
    )

    cible_data = [
        [Paragraph("URL analysée", label_style)],
        [Paragraph(target_url, url_style)],
        [Spacer(1, 0.3 * cm)],
        [Paragraph("Date du scan", label_style)],
        [Paragraph(report_date, date_style)],
    ]
    cible_table = Table(cible_data, colWidths=[col_w])
    cible_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ]
        )
    )
    story.append(cible_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Global risk status badge ──────────────────────────────────────────────
    status_color = _status_color(overall_status)
    risk_label_style = ParagraphStyle(
        "risk_label",
        fontName="Helvetica",
        fontSize=9,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    risk_status_style = ParagraphStyle(
        "risk_status",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=status_color,
        alignment=TA_CENTER,
    )
    explanations = {
        "OK": "Aucune vulnérabilité critique détectée. La posture de sécurité est satisfaisante.",
        "WARNING": "Des points d'amélioration ont été identifiés. Une action corrective est recommandée.",
        "CRITICAL": "Des vulnérabilités critiques ont été détectées. Une action immédiate est requise.",
    }
    risk_desc_style = ParagraphStyle(
        "risk_desc",
        fontName="Helvetica",
        fontSize=10,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
    )
    risk_data = [
        [Paragraph("NIVEAU DE RISQUE GLOBAL", risk_label_style)],
        [Paragraph(overall_status, risk_status_style)],
        [Paragraph(explanations.get(overall_status, ""), risk_desc_style)],
    ]
    risk_table = Table(risk_data, colWidths=[col_w])
    risk_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("ROUNDEDCORNERS", [6]),
            ]
        )
    )
    story.append(risk_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── CONFIDENTIEL footer ───────────────────────────────────────────────────
    conf_style = ParagraphStyle(
        "conf",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
    )
    conf_data = [
        [
            Paragraph(
                "CONFIDENTIEL — Document réservé au destinataire désigné", conf_style
            )
        ]
    ]
    conf_table = Table(conf_data, colWidths=[col_w], rowHeights=[0.9 * cm])
    conf_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD),
                ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(conf_table)
    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# Table of contents
# ---------------------------------------------------------------------------
def _build_toc(styles: dict[str, Any]) -> list:
    story = []
    story += _section_header("", "Table des matières", styles)

    toc_entries = [
        ("1.", "Résumé exécutif"),
        ("2.", "SSL / TLS"),
        ("3.", "Headers HTTP"),
        ("4.", "Ports réseau"),
        ("5.", "SCA — Dépendances"),
        ("6.", "Email Security (SPF / DKIM / DMARC)"),
        ("7.", "Cookie Security"),
        ("8.", "CORS"),
        ("9.", "IP Réputation"),
        ("10.", "DNS & Subdomains"),
        ("11.", "CMS Detection"),
        ("12.", "WAF Detection"),
        ("13.", "Data Breach"),
        ("14.", "Recommandations"),
    ]
    for num, title in toc_entries:
        story.append(Paragraph(f"<b>{num}</b>  {title}", styles["toc_entry"]))

    story.append(PageBreak())
    return story


# ---------------------------------------------------------------------------
# Section 1 — Résumé exécutif
# ---------------------------------------------------------------------------
def _build_executive_summary(
    overall_status: str, statuses: dict[str, str], styles: dict[str, Any], page_w: float
) -> list:
    story = []
    story += _section_header(1, "Résumé exécutif", styles)

    explanations = {
        "OK": "Aucune vulnérabilité critique détectée. La posture de sécurité est satisfaisante.",
        "WARNING": "Des points d'amélioration ont été identifiés. Une action corrective est recommandée.",
        "CRITICAL": "Des vulnérabilités critiques ont été détectées. Une action immédiate est requise.",
    }

    status_color = _status_color(overall_status)

    label_style = ParagraphStyle(
        "exec_label",
        fontName="Helvetica",
        fontSize=9,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    status_style = ParagraphStyle(
        "exec_status",
        fontName="Helvetica-Bold",
        fontSize=22,
        textColor=status_color,
        alignment=TA_CENTER,
    )
    desc_style = ParagraphStyle(
        "exec_desc",
        fontName="Helvetica",
        fontSize=11,
        textColor=COLOR_MUTED,
        alignment=TA_CENTER,
    )

    col_w = page_w - 4 * cm
    box_data = [
        [Paragraph("NIVEAU DE RISQUE GLOBAL", label_style)],
        [Paragraph(overall_status, status_style)],
        [Paragraph(explanations.get(overall_status, ""), desc_style)],
    ]
    box_table = Table(box_data, colWidths=[col_w])
    box_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("ROUNDEDCORNERS", [6]),
            ]
        )
    )
    story.append(box_table)
    story.append(Spacer(1, 0.8 * cm))

    # Per-module status table — header dark, no per-cell background coloring
    head_style = ParagraphStyle(
        "exec_th",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=COLOR_PRIMARY,
    )
    cell_style = ParagraphStyle(
        "exec_td",
        fontName="Helvetica",
        fontSize=10,
        textColor=COLOR_TEXT,
    )

    rows = [[Paragraph("Module", head_style), Paragraph("Statut", head_style)]]
    module_labels = {
        "ssl": "SSL / TLS",
        "headers": "Headers HTTP",
        "ports": "Ports réseau",
        "sca": "SCA — Dépendances",
        "email": "Email Security",
        "cookies": "Cookie Security",
        "cors": "CORS",
        "ip_rep": "IP Réputation",
        "dns": "DNS & Subdomains",
        "cms": "CMS Detection",
        "waf": "WAF Detection",
        "breach": "Data Breach",
    }
    for key, label in module_labels.items():
        if key in statuses:
            st = statuses[key]
            rows.append([Paragraph(label, cell_style), _status_inline(st)])
        else:
            rows.append(
                [
                    Paragraph(label, cell_style),
                    Paragraph(
                        "Non scanné",
                        ParagraphStyle(
                            "ns",
                            fontName="Helvetica",
                            fontSize=10,
                            textColor=COLOR_MUTED,
                        ),
                    ),
                ]
            )

    col_w_half = col_w / 2
    mod_table = Table(rows, colWidths=[col_w_half, col_w_half])
    mod_table.setStyle(_std_table_style())
    story.append(mod_table)
    return story
