"""
Module C — PDF Report Generator
Generates a professional audit report from Cyber-Scanner scan results.
"""

import os
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Brand colours  (dark theme — aligned with pdf_brand.py)
# ---------------------------------------------------------------------------
COLOR_CRITICAL    = colors.HexColor("#f87171")   # RED
COLOR_WARNING     = colors.HexColor("#fb923c")   # ORANGE
COLOR_OK          = colors.HexColor("#4ade80")   # GREEN
COLOR_PRIMARY     = colors.HexColor("#06b6d4")   # CYAN — text only
COLOR_BG          = colors.HexColor("#0f172a")   # page background
COLOR_CARD        = colors.HexColor("#1e293b")   # card / table header bg
COLOR_BORDER      = colors.HexColor("#334155")   # borders
COLOR_MUTED       = colors.HexColor("#94a3b8")   # secondary text
COLOR_TEXT        = colors.HexColor("#e2e8f0")   # primary text

# Aliases kept for backward compat within this file
COLOR_WHITE       = colors.white
COLOR_LIGHT_BORDER = COLOR_BORDER
COLOR_ROW_ALT     = COLOR_CARD

from scanner.constants import PORT_NAMES, HEADER_RECOMMENDATIONS


# ---------------------------------------------------------------------------
# Page template with footer
# ---------------------------------------------------------------------------
class AuditDocTemplate(BaseDocTemplate):
    """Custom doc template that renders a footer on every page."""

    def __init__(self, filename: str, report_date: str, **kwargs):
        super().__init__(filename, **kwargs)
        self.report_date = report_date
        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="main",
        )
        template = PageTemplate(id="main", frames=[frame], onPage=self._draw_footer)
        self.addPageTemplates([template])

    def _draw_footer(self, canvas, doc):
        """Render dark background, top band (scan blue) and footer on every page."""
        from reportlab.lib.pagesizes import A4
        page_w, page_h = A4

        canvas.saveState()

        # ── Full-page dark background ─────────────────────────────────────────
        canvas.setFillColor(COLOR_BG)   # DARK_BG #0f172a
        canvas.rect(0, 0, page_w, page_h, fill=1, stroke=0)

        # ── Top band (scan blue, #3b82f6 at 30 % opacity) ────────────────────
        scan_color = colors.HexColor("#3b82f6")
        r, g, b    = scan_color.red, scan_color.green, scan_color.blue
        band_h     = 10 * mm
        band_y     = page_h - band_h

        canvas.setFillColorRGB(r, g, b, alpha=0.30)
        canvas.rect(0, band_y, page_w, band_h, fill=1, stroke=0)

        # Top edge line (2 px)
        canvas.setStrokeColor(scan_color)
        canvas.setLineWidth(2)
        canvas.line(0, page_h - 1, page_w, page_h - 1)

        # "CS" logo mark
        left_margin = doc.leftMargin
        logo_size   = 6 * mm
        logo_x      = left_margin
        logo_y      = band_y + (band_h - logo_size) / 2
        canvas.setFillColor(COLOR_PRIMARY)   # CYAN
        canvas.roundRect(logo_x, logo_y, logo_size, logo_size, radius=1.5 * mm, fill=1, stroke=0)
        canvas.setFillColor(COLOR_WHITE)
        canvas.setFont("Helvetica-Bold", 6)
        canvas.drawCentredString(logo_x + logo_size / 2, logo_y + 1.5 * mm, "CS")

        # "CyberScan" label
        text_x = logo_x + logo_size + 3 * mm
        mid_y  = band_y + band_h / 2 - 1.5 * mm
        canvas.setFillColor(COLOR_WHITE)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawString(text_x, mid_y, "CyberScan")

        # Pipe separator
        sep_x = text_x + 60
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 9)
        canvas.drawString(sep_x, mid_y, "|")

        # Document title
        canvas.setFillColor(scan_color)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(sep_x + 8, mid_y, "Rapport d'Audit")

        # Date right-aligned in band
        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(page_w - left_margin, mid_y, self.report_date.split(" ")[0])

        # ── Footer ────────────────────────────────────────────────────────────
        footer_y = 8 * mm
        canvas.setStrokeColor(COLOR_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(left_margin, footer_y, left_margin + doc.width, footer_y)

        canvas.setFillColor(colors.HexColor("#94a3b8"))
        canvas.setFont("Helvetica", 7)

        canvas.drawString(left_margin, footer_y - 5 * mm, "CyberScan \u2014 confidentiel")
        canvas.drawCentredString(page_w / 2, footer_y - 5 * mm, f"Page {doc.page}")
        canvas.drawRightString(left_margin + doc.width, footer_y - 5 * mm, self.report_date)

        canvas.restoreState()


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
def _build_styles() -> dict[str, Any]:
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=COLOR_TEXT,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontName="Helvetica",
            fontSize=14,
            textColor=COLOR_MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_confidential": ParagraphStyle(
            "cover_confidential",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=COLOR_WARNING,
            alignment=TA_CENTER,
        ),
        "section_title": ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=COLOR_TEXT,
            spaceBefore=18,
            spaceAfter=8,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry",
            fontName="Helvetica",
            fontSize=11,
            textColor=COLOR_PRIMARY,
            spaceAfter=5,
            leftIndent=12,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_MUTED,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_MUTED,
            spaceAfter=5,
            leftIndent=16,
            bulletIndent=4,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=COLOR_PRIMARY,
        ),
        "cell": ParagraphStyle(
            "cell",
            fontName="Helvetica",
            fontSize=9,
            textColor=COLOR_MUTED,
        ),
    }
    return styles


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------
def _status_color(status: str) -> colors.Color:
    mapping = {
        "OK": COLOR_OK,
        "WARNING": COLOR_WARNING,
        "CRITICAL": COLOR_CRITICAL,
    }
    return mapping.get(status, colors.HexColor("#64748B"))


def _status_bullet(status: str) -> str:
    """Return a bullet+text string for inline status display (no background fill)."""
    labels = {
        "OK": "● OK",
        "WARNING": "● WARNING",
        "CRITICAL": "● CRITICAL",
    }
    return labels.get(status, f"● {status}")


def _status_inline(status: str) -> Paragraph:
    """Return a Paragraph with colored bullet text — no background coloring."""
    c = _status_color(status)
    st = ParagraphStyle(
        "inline_status",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=c,
    )
    return Paragraph(_status_bullet(status), st)


# ---------------------------------------------------------------------------
# Standard table style factory
# ---------------------------------------------------------------------------
def _std_table_style(extra: list | None = None) -> TableStyle:
    """
    Returns the standard dark-theme table style:
    - Header row: COLOR_CARD bg, COLOR_PRIMARY text, bold 10pt
    - Data rows: alternating COLOR_BG / COLOR_CARD
    - No INNERGRID — only BOX + LINEBELOW
    - Padding: top/bottom=8, left/right=12
    """
    base = [
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0),  COLOR_CARD),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  COLOR_PRIMARY),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  10),
        # Data rows alternating
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_BG, COLOR_CARD]),
        # Text color for data cells
        ("TEXTCOLOR",    (0, 1), (-1, -1), COLOR_TEXT),
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 9),
        # Borders: box + horizontal separators only
        ("BOX",          (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("LINEBELOW",    (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        # Alignment / padding
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 8),
        ("LEFTPADDING",  (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]
    if extra:
        base.extend(extra)
    return TableStyle(base)


# ---------------------------------------------------------------------------
# Section header helper
# ---------------------------------------------------------------------------
def _section_header(num: str | int, title: str, styles: dict[str, Any]) -> list:
    """
    Returns a list of flowables representing a styled section header:
    - Left accent bar (cyan 4mm) + bold title text
    - Thin HR separator
    """
    accent_style = ParagraphStyle(
        "sh_accent",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=COLOR_TEXT,
    )
    # Accent bar as a tiny filled table cell
    bar_data = [[""]]
    bar_table = Table(bar_data, colWidths=[4 * mm], rowHeights=[0.6 * cm])
    bar_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))

    title_para = Paragraph(f"{num}. {title}", accent_style)

    header_table = Table(
        [[bar_table, title_para]],
        colWidths=[4 * mm + 6, None],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))

    return [
        Spacer(1, 0.5 * cm),
        header_table,
        Spacer(1, 0.15 * cm),
        HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceAfter=0),
        Spacer(1, 0.3 * cm),
    ]


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------
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
    logo_badge.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_PRIMARY),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [6]),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))

    logo_row = Table(
        [[logo_badge, Paragraph("CyberScan", cs_label_style)]],
        colWidths=[2 * cm, col_w - 2 * cm],
    )
    logo_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    story.append(Spacer(1, 2 * cm))
    story.append(logo_row)
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Rapport d'Audit de Sécurité", cs_sub_style))
    story.append(Spacer(1, 0.4 * cm))
    story.append(HRFlowable(width="100%", thickness=1, color=COLOR_BORDER, spaceAfter=0))
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
    cible_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_CARD),
        ("BOX",           (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN",         (0, 0), (-1, -1), "LEFT"),
    ]))
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
    risk_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_CARD),
        ("BOX",           (0, 0), (-1, -1), 1, COLOR_BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", [6]),
    ]))
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
    conf_data = [[Paragraph("CONFIDENTIEL — Document réservé au destinataire désigné", conf_style)]]
    conf_table = Table(conf_data, colWidths=[col_w], rowHeights=[0.9 * cm])
    conf_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), COLOR_CARD),
        ("BOX",        (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
    ]))
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
        ("1.",  "Résumé exécutif"),
        ("2.",  "SSL / TLS"),
        ("3.",  "Headers HTTP"),
        ("4.",  "Ports réseau"),
        ("5.",  "SCA — Dépendances"),
        ("6.",  "Email Security (SPF / DKIM / DMARC)"),
        ("7.",  "Cookie Security"),
        ("8.",  "CORS"),
        ("9.",  "IP Réputation"),
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
    box_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), COLOR_CARD),
        ("BOX",           (0, 0), (-1, -1), 1, COLOR_BORDER),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("ROUNDEDCORNERS", [6]),
    ]))
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
        "ssl":     "SSL / TLS",
        "headers": "Headers HTTP",
        "ports":   "Ports réseau",
        "sca":     "SCA — Dépendances",
        "email":   "Email Security",
        "cookies": "Cookie Security",
        "cors":    "CORS",
        "ip_rep":  "IP Réputation",
        "dns":     "DNS & Subdomains",
        "cms":     "CMS Detection",
        "waf":     "WAF Detection",
        "breach":  "Data Breach",
    }
    for key, label in module_labels.items():
        if key in statuses:
            st = statuses[key]
            rows.append([Paragraph(label, cell_style), _status_inline(st)])
        else:
            rows.append([
                Paragraph(label, cell_style),
                Paragraph("Non scanné", ParagraphStyle(
                    "ns", fontName="Helvetica", fontSize=10, textColor=COLOR_MUTED
                )),
            ])

    col_w_half = col_w / 2
    mod_table = Table(rows, colWidths=[col_w_half, col_w_half])
    mod_table.setStyle(_std_table_style())
    story.append(mod_table)
    return story


# ---------------------------------------------------------------------------
# Section 2 — SSL/TLS
# ---------------------------------------------------------------------------
def _build_ssl_section(ssl_result: dict[str, Any], styles: dict[str, Any], page_w: float) -> list:
    story = []
    story += _section_header(2, "SSL / TLS", styles)

    head_style = ParagraphStyle("th2", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td2", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)

    if ssl_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline("CRITICAL")],
            [Paragraph("Erreur", cell_style), Paragraph(str(ssl_result["error"]), cell_style)],
        ]
    else:
        days = ssl_result.get("days_remaining", 0) or 0
        days_color = COLOR_OK if days >= 30 else (COLOR_WARNING if days >= 7 else COLOR_CRITICAL)
        days_style = ParagraphStyle("dy2", fontName="Helvetica-Bold", fontSize=10, textColor=days_color)

        valid_text = "Oui" if ssl_result.get("valid") else "Non"
        valid_color = COLOR_OK if ssl_result.get("valid") else COLOR_CRITICAL
        valid_style = ParagraphStyle("vl2", fontName="Helvetica-Bold", fontSize=10, textColor=valid_color)

        tls_ok = ssl_result.get("tls_ok", False)
        tls_text = "Oui (>= TLS 1.2)" if tls_ok else "Non (protocole obsolète)"
        tls_color = COLOR_OK if tls_ok else COLOR_CRITICAL
        tls_style = ParagraphStyle("tl2", fontName="Helvetica-Bold", fontSize=10, textColor=tls_color)

        status = ssl_result.get("status", "CRITICAL")
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(status)],
            [Paragraph("Certificat valide", cell_style), Paragraph(valid_text, valid_style)],
            [Paragraph("Date d'expiration", cell_style), Paragraph(str(ssl_result.get("expiry_date", "—")), cell_style)],
            [Paragraph("Jours restants", cell_style), Paragraph(str(days), days_style)],
            [Paragraph("Protocole", cell_style), Paragraph(str(ssl_result.get("protocol", "—")), cell_style)],
            [Paragraph("TLS OK", cell_style), Paragraph(tls_text, tls_style)],
        ]

    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.38, col_w * 0.62])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 3 — HTTP Headers
# ---------------------------------------------------------------------------
def _build_headers_section(headers_result: dict[str, Any], styles: dict[str, Any], page_w: float) -> list:
    story = []
    story += _section_header(3, "Headers HTTP", styles)

    head_style = ParagraphStyle("th3", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td3", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)

    if headers_result.get("error"):
        rows = [
            [Paragraph("Header", head_style), Paragraph("Statut", head_style)],
            [Paragraph("Erreur", cell_style), Paragraph(str(headers_result["error"]), cell_style)],
        ]
    else:
        rows = [[Paragraph("Header de sécurité", head_style), Paragraph("Présence", head_style)]]

        found = set(headers_result.get("headers_found", []))
        missing = set(headers_result.get("headers_missing", []))
        all_headers = list(found) + list(missing)

        for header in all_headers:
            if header in found:
                present_style = ParagraphStyle("ok3", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_OK)
                rows.append([Paragraph(header, cell_style), Paragraph("✓  Présent", present_style)])
            else:
                absent_style = ParagraphStyle("cr3", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_CRITICAL)
                rows.append([Paragraph(header, cell_style), Paragraph("✗  Absent", absent_style)])

        score = headers_result.get("score", 0)
        score_color = COLOR_OK if score == 6 else (COLOR_WARNING if score >= 4 else COLOR_CRITICAL)
        score_style = ParagraphStyle("sc3", fontName="Helvetica-Bold", fontSize=10, textColor=score_color)
        rows.append([
            Paragraph("Score total", ParagraphStyle("stb3", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_TEXT)),
            Paragraph(f"{score}/6", score_style),
        ])

    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.65, col_w * 0.35])
    # Last row gets a slightly distinct bg to stand out as summary
    t.setStyle(_std_table_style([
        ("BACKGROUND", (0, -1), (-1, -1), COLOR_CARD),
    ]))
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 4 — Ports réseau
# ---------------------------------------------------------------------------
def _build_ports_section(port_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(4, "Ports réseau", styles)

    head_style = ParagraphStyle("th4", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td4", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or port_result is None:
        rows = [
            [Paragraph("Résultat", head_style)],
            [Paragraph("Non scanné (option --skip-ports activée)", cell_style)],
        ]
        t = Table(rows, colWidths=[col_w])
    elif port_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline("CRITICAL")],
            [Paragraph("Erreur", cell_style), Paragraph(str(port_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        open_ports = port_result.get("open_ports", [])
        critical_ports = port_result.get("critical_ports", [])

        rows = [[Paragraph("Port", head_style), Paragraph("Service", head_style), Paragraph("Criticité", head_style)]]

        if open_ports:
            for port_info in open_ports:
                if isinstance(port_info, dict):
                    port_num = port_info.get("port", 0)
                    service  = port_info.get("service", PORT_NAMES.get(port_num, "unknown"))
                    crit_raw = port_info.get("criticality", "")
                    is_critical = crit_raw.lower() in ("critique", "critical", "high", "danger")
                else:
                    port_num    = port_info
                    service     = PORT_NAMES.get(port_num, "unknown")
                    is_critical = port_num in (critical_ports or [])
                crit_text = "Critique" if is_critical else "Normal"
                crit_style = ParagraphStyle(
                    "cp4",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=COLOR_CRITICAL if is_critical else COLOR_OK,
                )
                rows.append([
                    Paragraph(str(port_num), cell_style),
                    Paragraph(service, cell_style),
                    Paragraph(crit_text, crit_style),
                ])
        else:
            rows.append([
                Paragraph("—", cell_style),
                Paragraph("Aucun port ouvert", cell_style),
                Paragraph("● OK", ParagraphStyle("ok4", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_OK)),
            ])

        t = Table(rows, colWidths=[col_w * 0.2, col_w * 0.5, col_w * 0.3])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 5 — SCA (Software Composition Analysis)
# ---------------------------------------------------------------------------
def _build_sca_section(sca_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(5, "SCA — Analyse des dépendances", styles)

    head_style = ParagraphStyle("th5", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td5", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not sca_result:
        rows = [
            [Paragraph("Résultat", head_style)],
            [Paragraph("Non scanné (utiliser --requirements ou --package-json pour activer)", cell_style)],
        ]
        t = Table(rows, colWidths=[col_w])
        t.setStyle(_std_table_style())
        story.append(t)
        return story

    if sca_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline("CRITICAL")],
            [Paragraph("Erreur", cell_style), Paragraph(str(sca_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
        t.setStyle(_std_table_style())
        story.append(t)
        return story

    vulns = sca_result.get("vulns", [])
    total_pkgs = sca_result.get("total_packages", 0)
    total_vulns = sca_result.get("total_vulns", 0)

    vuln_color = COLOR_OK if total_vulns == 0 else (COLOR_WARNING if sca_result.get("status") == "WARNING" else COLOR_CRITICAL)
    vuln_style = ParagraphStyle("vs5", fontName="Helvetica-Bold", fontSize=10, textColor=vuln_color)

    summary_rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        [Paragraph("Packages scannés", cell_style), Paragraph(str(total_pkgs), cell_style)],
        [Paragraph("Vulnérabilités trouvées", cell_style), Paragraph(str(total_vulns), vuln_style)],
    ]
    t_summary = Table(summary_rows, colWidths=[col_w * 0.45, col_w * 0.55])
    t_summary.setStyle(_std_table_style())
    story.append(t_summary)

    if vulns:
        story.append(Spacer(1, 0.4 * cm))
        sev_colors = {
            "CRITICAL": COLOR_CRITICAL,
            "HIGH": COLOR_CRITICAL,
            "MEDIUM": COLOR_WARNING,
            "LOW": colors.HexColor("#3B82F6"),
            "UNKNOWN": COLOR_MUTED,
        }
        vuln_head = [
            Paragraph("Package", head_style),
            Paragraph("CVE / ID", head_style),
            Paragraph("Sévérité", head_style),
            Paragraph("Résumé", head_style),
        ]
        vuln_rows = [vuln_head]
        for v in vulns:
            sev = v.get("severity", "UNKNOWN")
            sc = sev_colors.get(sev, COLOR_MUTED)
            sev_cell_style = ParagraphStyle("sc5", fontName="Helvetica-Bold", fontSize=9, textColor=sc)
            cve_str = "\n".join(v.get("cve_ids", ["N/A"]))
            summary_text = v.get("summary", "")[:180]
            vuln_rows.append([
                Paragraph(f"{v['package']}\n{v['version']}", ParagraphStyle("pkg5", fontName="Helvetica", fontSize=9, textColor=COLOR_TEXT)),
                Paragraph(cve_str, ParagraphStyle("cv5", fontName="Helvetica", fontSize=9, textColor=COLOR_TEXT)),
                Paragraph(sev, sev_cell_style),
                Paragraph(summary_text, ParagraphStyle("sm5", fontName="Helvetica", fontSize=8, textColor=COLOR_MUTED)),
            ])
        t_vulns = Table(
            vuln_rows,
            colWidths=[col_w * 0.18, col_w * 0.22, col_w * 0.14, col_w * 0.46],
        )
        t_vulns.setStyle(_std_table_style([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(t_vulns)

    return story


# ---------------------------------------------------------------------------
# Section 6 — Email Security
# ---------------------------------------------------------------------------
def _build_email_section(email_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(6, "Email Security (SPF / DKIM / DMARC)", styles)

    head_style = ParagraphStyle("th6", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td6", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not email_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    elif email_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Erreur", cell_style), Paragraph(str(email_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        def flag_cell(found: bool, ok_text: str, bad_text: str) -> Paragraph:
            if found:
                return Paragraph(ok_text, ParagraphStyle("ok6", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_OK))
            return Paragraph(bad_text, ParagraphStyle("cr6", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_CRITICAL))

        spf = email_result.get("spf", {})
        dkim = email_result.get("dkim", {})
        dmarc = email_result.get("dmarc", {})
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(email_result.get("status", "OK"))],
            [Paragraph("SPF", cell_style), flag_cell(spf.get("found", False), f"Présent {'(strict)' if spf.get('strict') else '(~all)'}", "Absent")],
            [Paragraph("DKIM", cell_style), flag_cell(dkim.get("found", False), f"Présent (selector: {dkim.get('selector', '?')})", "Non détecté")],
            [Paragraph("DMARC", cell_style), flag_cell(dmarc.get("found", False), f"Présent (p={dmarc.get('policy', '?')})", "Absent")],
        ]
        for issue in email_result.get("issues", []):
            rows.append([
                Paragraph("Issue", ParagraphStyle("is6", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_WARNING)),
                Paragraph(issue, cell_style),
            ])
        t = Table(rows, colWidths=[col_w * 0.3, col_w * 0.7])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 7 — Cookie Security
# ---------------------------------------------------------------------------
def _build_cookie_section(cookie_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(7, "Cookie Security", styles)

    head_style = ParagraphStyle("th7", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td7", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not cookie_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    elif cookie_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Erreur", cell_style), Paragraph(str(cookie_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        issues = cookie_result.get("issues", [])
        rows = [[Paragraph("Cookie", head_style), Paragraph("Problème", head_style)]]
        if issues:
            for issue in issues:
                rows.append([
                    Paragraph(issue["cookie"], cell_style),
                    Paragraph(issue["issue"], ParagraphStyle("warn7", fontName="Helvetica", fontSize=10, textColor=COLOR_WARNING)),
                ])
        else:
            rows.append([
                Paragraph("—", cell_style),
                Paragraph("Tous les cookies sont correctement sécurisés",
                          ParagraphStyle("ok7", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_OK)),
            ])

        summary_style = ParagraphStyle("sm7", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_TEXT)
        total_issues = cookie_result.get("total_issues", 0)
        ic = COLOR_OK if total_issues == 0 else (COLOR_WARNING if cookie_result.get("status") == "WARNING" else COLOR_CRITICAL)
        rows.append([Paragraph("Total cookies", summary_style), Paragraph(str(cookie_result.get("total_cookies", 0)), cell_style)])
        rows.append([Paragraph("Total issues", summary_style), Paragraph(str(total_issues), ParagraphStyle("tc7", fontName="Helvetica-Bold", fontSize=10, textColor=ic))])
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])

    t.setStyle(_std_table_style([
        ("BACKGROUND", (0, -2), (-1, -1), COLOR_CARD),
    ]))
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 8 — CORS
# ---------------------------------------------------------------------------
def _build_cors_section(cors_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(8, "CORS", styles)

    head_style = ParagraphStyle("th8", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td8", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not cors_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    elif cors_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Erreur", cell_style), Paragraph(str(cors_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])
    else:
        vuln = cors_result.get("vulnerable", False)
        vuln_style = ParagraphStyle("vl8", fontName="Helvetica-Bold", fontSize=10,
                                    textColor=COLOR_CRITICAL if vuln else COLOR_OK)
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(cors_result.get("status", "OK"))],
            [Paragraph("Allow-Origin", cell_style), Paragraph(cors_result.get("allow_origin") or "non défini", cell_style)],
            [Paragraph("Allow-Credentials", cell_style), Paragraph(cors_result.get("allow_credentials") or "non défini", cell_style)],
            [Paragraph("Vulnérable", cell_style), Paragraph("Oui" if vuln else "Non", vuln_style)],
        ]
        for issue in cors_result.get("issues", []):
            rows.append([
                Paragraph("Issue", ParagraphStyle("is8", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_WARNING)),
                Paragraph(issue, cell_style),
            ])
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 9 — IP Réputation
# ---------------------------------------------------------------------------
def _build_ip_reputation_section(ip_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(9, "IP Réputation (DNSBL)", styles)

    head_style = ParagraphStyle("th9", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td9", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not ip_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    elif ip_result.get("error") and not ip_result.get("ip"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Erreur", cell_style), Paragraph(str(ip_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        listed = ip_result.get("listed_in", [])
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(ip_result.get("status", "OK"))],
            [Paragraph("IP", cell_style), Paragraph(str(ip_result.get("ip", "—")), cell_style)],
            [Paragraph("Blacklists", cell_style),
             Paragraph(str(ip_result.get("total_listed", 0)),
                       ParagraphStyle("bl9", fontName="Helvetica-Bold", fontSize=10,
                                      textColor=COLOR_CRITICAL if listed else COLOR_OK))],
        ]
        for entry in listed:
            rows.append([
                Paragraph(entry["label"], ParagraphStyle("lb9", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_CRITICAL)),
                Paragraph(entry["category"], cell_style),
            ])
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 10 — DNS & Subdomains
# ---------------------------------------------------------------------------
def _build_dns_section(dns_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(10, "DNS & Subdomains", styles)

    head_style = ParagraphStyle("th10", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td10", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not dns_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    else:
        zt = dns_result.get("zone_transfer", {})
        zt_style = ParagraphStyle("zt10", fontName="Helvetica-Bold", fontSize=10,
                                  textColor=COLOR_CRITICAL if zt.get("vulnerable") else COLOR_OK)
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(dns_result.get("status", "OK"))],
            [Paragraph("Subdomains trouvés", cell_style), Paragraph(str(dns_result.get("total_found", 0)), cell_style)],
            [Paragraph("Zone Transfer", cell_style),
             Paragraph("VULNERABLE" if zt.get("vulnerable") else "Refusé", zt_style)],
        ]
        for s in dns_result.get("found", [])[:10]:
            rows.append([
                Paragraph(s["subdomain"], ParagraphStyle("sub10", fontName="Helvetica", fontSize=9, textColor=COLOR_PRIMARY)),
                Paragraph(s["ip"], cell_style),
            ])
        if dns_result.get("total_found", 0) > 10:
            rows.append([Paragraph(f"... et {dns_result['total_found'] - 10} autres", cell_style), Paragraph("", cell_style)])
        t = Table(rows, colWidths=[col_w * 0.55, col_w * 0.45])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 11 — CMS Detection
# ---------------------------------------------------------------------------
def _build_cms_section(cms_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(11, "CMS Detection", styles)

    head_style = ParagraphStyle("th11", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td11", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not cms_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    else:
        cms = cms_result.get("cms", "Unknown")
        version = cms_result.get("version")
        cms_color = COLOR_OK if cms == "Unknown" else (COLOR_CRITICAL if version else COLOR_WARNING)
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(cms_result.get("status", "OK"))],
            [Paragraph("CMS détecté", cell_style),
             Paragraph(cms, ParagraphStyle("cms11", fontName="Helvetica-Bold", fontSize=10, textColor=cms_color))],
        ]
        if version:
            rows.append([
                Paragraph("Version exposée", cell_style),
                Paragraph(version, ParagraphStyle("ver11", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_CRITICAL)),
            ])
        rows.append([Paragraph("Confidence", cell_style), Paragraph(str(cms_result.get("confidence", 0)), cell_style)])
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 12 — WAF Detection
# ---------------------------------------------------------------------------
def _build_waf_section(waf_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(12, "WAF Detection", styles)

    head_style = ParagraphStyle("th12", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td12", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not waf_result:
        rows = [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    else:
        detected = waf_result.get("detected", False)
        det_style = ParagraphStyle("det12", fontName="Helvetica-Bold", fontSize=10,
                                   textColor=COLOR_OK if detected else COLOR_WARNING)
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(waf_result.get("status", "OK"))],
            [Paragraph("WAF détecté", cell_style), Paragraph("Oui" if detected else "Non", det_style)],
        ]
        if waf_result.get("waf_name"):
            rows.append([
                Paragraph("Nom", cell_style),
                Paragraph(waf_result["waf_name"], ParagraphStyle("wn12", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_OK)),
            ])
        if waf_result.get("method"):
            rows.append([Paragraph("Méthode détection", cell_style), Paragraph(waf_result["method"], cell_style)])
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 13 — Data Breach
# ---------------------------------------------------------------------------
def _build_breach_section(breach_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(13, "Data Breach (HIBP)", styles)

    head_style = ParagraphStyle("th13", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    cell_style = ParagraphStyle("td13", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT)
    col_w = page_w - 4 * cm

    if skipped or not breach_result:
        rows = [[Paragraph("Résultat", head_style)],
                [Paragraph("Non scanné (utiliser --breach-email ou --breach-domain)", cell_style)]]
        t = Table(rows, colWidths=[col_w])
    elif breach_result.get("error") and breach_result.get("status") == "WARNING":
        rows = [[Paragraph("Résultat", head_style)], [Paragraph(str(breach_result["error"]), cell_style)]]
        t = Table(rows, colWidths=[col_w])
    else:
        total = breach_result.get("total", 0)
        total_color = COLOR_OK if total == 0 else (COLOR_WARNING if breach_result.get("status") == "WARNING" else COLOR_CRITICAL)
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(breach_result.get("status", "OK"))],
            [Paragraph("Cible", cell_style), Paragraph(breach_result.get("target", ""), cell_style)],
            [Paragraph("Fuites trouvées", cell_style),
             Paragraph(str(total), ParagraphStyle("tc13", fontName="Helvetica-Bold", fontSize=10, textColor=total_color))],
        ]
        for b in breach_result.get("breaches", []):
            rows.append([
                Paragraph(b["name"], ParagraphStyle("bn13", fontName="Helvetica-Bold", fontSize=9, textColor=COLOR_CRITICAL)),
                Paragraph(f"{b.get('breach_date','')} — {b.get('pwn_count',0):,} comptes", cell_style),
            ])
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 14 — Technology Fingerprint
# ---------------------------------------------------------------------------
def _build_tech_section(tech_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(14, "Technology Fingerprint", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-tech).", styles["body"]))
        return story

    status = tech_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    head_style = ParagraphStyle("th14", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [[Paragraph("Catégorie", head_style), Paragraph("Technologies détectées", head_style)]]
    for cat, names in tech_result.get("technologies", {}).items():
        rows.append([cat.capitalize(), ", ".join(names)])
    if len(rows) == 1:
        rows.append(["—", "Aucune technologie identifiée"])

    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.3, col_w * 0.7])
    t.setStyle(_std_table_style())
    story.append(t)

    if tech_result.get("error"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"⚠ {tech_result['error']}", styles["body"]))
    return story


# ---------------------------------------------------------------------------
# Section 15 — TLS Deep Audit
# ---------------------------------------------------------------------------
def _build_tls_section(tls_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(15, "Audit TLS approfondi", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-tls).", styles["body"]))
        return story

    status = tls_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    hsts = tls_result.get("hsts", {})
    rows = [
        ["Protocoles supportés", ", ".join(tls_result.get("supported_protocols", [])) or "—"],
        ["Protocoles faibles",   ", ".join(tls_result.get("weak_protocols", [])) or "Aucun"],
        ["Chiffrements faibles", ", ".join(tls_result.get("weak_ciphers", [])) or "Aucun"],
        ["HSTS",                 "Présent" if hsts.get("present") else "Absent"],
        ["HSTS max-age",         str(hsts.get("max_age", "—"))],
        ["HSTS preload",         "Oui" if hsts.get("preload") else "Non"],
    ]
    cert = tls_result.get("certificate")
    if cert:
        rows += [
            ["Cert subject",  cert.get("subject", "—")],
            ["Cert issuer",   cert.get("issuer", "—")],
            ["Cert expires",  cert.get("not_after", "—")],
        ]

    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 16 — Subdomain Takeover
# ---------------------------------------------------------------------------
def _build_takeover_section(takeover_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(16, "Subdomain Takeover", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-takeover).", styles["body"]))
        return story

    status = takeover_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        f"Sous-domaines vérifiés : {takeover_result.get('total_checked', 0)} — "
        f"Vulnérables : {takeover_result.get('total_vulnerable', 0)}",
        styles["body"],
    ))

    vulns = takeover_result.get("vulnerable", [])
    if vulns:
        story.append(Spacer(1, 0.2 * cm))
        head_style = ParagraphStyle("th16", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
        rows = [[Paragraph("Sous-domaine", head_style), Paragraph("Service", head_style), Paragraph("Raison", head_style)]]
        for v in vulns:
            rows.append([v["subdomain"], v.get("service", "—"), v.get("reason", "—")])
        col_w = page_w - 4 * cm
        t = Table(rows, colWidths=[col_w * 0.38, col_w * 0.22, col_w * 0.40])
        # Takeover header gets critical color to signal danger
        t.setStyle(_std_table_style([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3d1515")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), COLOR_CRITICAL),
        ]))
        story.append(t)

    if takeover_result.get("error"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(takeover_result["error"], styles["body"]))
    return story


# ---------------------------------------------------------------------------
# Section 17 — Threat Intelligence
# ---------------------------------------------------------------------------
def _build_threat_intel_section(ti_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(17, "Threat Intelligence (Shodan)", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-threat).", styles["body"]))
        return story

    status = ti_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    cves  = ti_result.get("cves", [])
    ports = ti_result.get("open_ports", [])
    abuse = ti_result.get("abuse_score")

    head_style = ParagraphStyle("th17", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["IP",           str(ti_result.get("ip", "—"))],
        ["Ports ouverts", ", ".join(str(p) for p in ports) if ports else "—"],
        ["CVEs",          ", ".join(cves[:8]) + ("…" if len(cves) > 8 else "") if cves else "Aucun"],
        ["Tags Shodan",   ", ".join(ti_result.get("tags", [])) or "—"],
        ["Abuse score",   f"{abuse}/100" if abuse is not None else "—"],
    ]
    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.3, col_w * 0.7])
    t.setStyle(_std_table_style())
    story.append(t)

    if ti_result.get("error"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"⚠ {ti_result['error']}", styles["body"]))
    return story


# ---------------------------------------------------------------------------
# Section 18 — HTTP Methods
# ---------------------------------------------------------------------------
def _build_http_methods_section(methods_result: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(18, "Méthodes HTTP dangereuses", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-methods).", styles["body"]))
        return story

    status = methods_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    dangerous = methods_result.get("dangerous_allowed", [])
    allowed   = methods_result.get("allowed_methods", [])
    declared  = methods_result.get("options_declared", [])

    head_style = ParagraphStyle("th18", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["OPTIONS déclare",    ", ".join(declared) if declared else "—"],
        ["Méthodes autorisées", ", ".join(allowed) if allowed else "Aucune"],
        ["Méthodes dangereuses", ", ".join(dangerous) if dangerous else "Aucune"],
    ]
    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    t.setStyle(_std_table_style())
    story.append(t)

    probes = methods_result.get("probes", [])
    if probes:
        story.append(Spacer(1, 0.3 * cm))
        probe_head = [Paragraph("Méthode", head_style), Paragraph("Code HTTP", head_style), Paragraph("Acceptée", head_style)]
        probe_rows = [probe_head]
        for p in probes:
            code = str(p["status_code"]) if p["status_code"] else "Erreur"
            accepted = "OUI" if p["allowed"] else "non"
            accepted_style = ParagraphStyle(
                "acc18",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=COLOR_CRITICAL if p["allowed"] else COLOR_OK,
            )
            probe_rows.append([
                p["method"],
                code,
                Paragraph(accepted, accepted_style),
            ])
        t2 = Table(probe_rows, colWidths=[col_w * 0.25, col_w * 0.35, col_w * 0.40])
        t2.setStyle(_std_table_style())
        story.append(t2)
    return story


# ---------------------------------------------------------------------------
# Section 19 — Open Redirect
# ---------------------------------------------------------------------------
def _build_open_redirect_section(r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(19, "Open Redirect", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-redirects).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    col_w = page_w - 4 * cm
    head_style = ParagraphStyle("th19", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    vuln_text = "OUI" if r.get("vulnerable") else "Non"
    vuln_style = ParagraphStyle(
        "vl19",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=COLOR_CRITICAL if r.get("vulnerable") else COLOR_OK,
    )
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["Probes envoyées", str(r.get("tested", 0))],
        ["Vulnérable", Paragraph(vuln_text, vuln_style)],
    ]
    findings = r.get("findings", [])
    for f in findings:
        rows.append([f"Param: {f['param']}", f"→ {f['location'][:60]}"])

    t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 20 — Clickjacking
# ---------------------------------------------------------------------------
def _build_clickjacking_section(r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(20, "Clickjacking", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-clickjacking).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    xfo = r.get("xfo", {})
    csp = r.get("csp_frame_ancestors", {})
    col_w = page_w - 4 * cm

    head_style = ParagraphStyle("th20", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["X-Frame-Options",      xfo.get("value") or "Absent"],
        ["XFO protégé",          "Oui" if xfo.get("protected") else "Non"],
        ["CSP frame-ancestors",  csp.get("value") or "Absent"],
        ["CSP protégé",          "Oui" if csp.get("protected") else "Non"],
        ["Vulnérable clickjacking", "OUI" if r.get("vulnerable") else "Non"],
    ]
    t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 21 — Directory Listing
# ---------------------------------------------------------------------------
def _build_dirlist_section(r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(21, "Directory Listing & Chemins sensibles", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-dirlist).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    findings = r.get("findings", [])
    if not findings:
        story.append(Paragraph("Aucun chemin sensible exposé.", styles["body"]))
        return story

    col_w = page_w - 4 * cm
    head_style = ParagraphStyle("th21", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [[
        Paragraph("Chemin", head_style),
        Paragraph("Catégorie", head_style),
        Paragraph("Sévérité", head_style),
        Paragraph("HTTP", head_style),
    ]]
    for f in findings:
        rows.append([f["path"], f["category"], f["severity"], str(f["status_code"])])

    t = Table(rows, colWidths=[col_w * 0.38, col_w * 0.22, col_w * 0.22, col_w * 0.18])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 22 — Robots & Sitemap
# ---------------------------------------------------------------------------
def _build_robots_section(r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(22, "Robots.txt & Sitemap", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-robots).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    col_w = page_w - 4 * cm
    sensitive = r.get("sensitive_disallowed", [])
    head_style = ParagraphStyle("th22", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["robots.txt",         "Trouvé" if r.get("robots_found") else "Absent"],
        ["Disallow entries",   str(len(r.get("disallowed_paths", [])))],
        ["Chemins sensibles",  ", ".join(sensitive[:6]) if sensitive else "Aucun"],
        ["Sitemap",            "Trouvé" if r.get("sitemap_found") else "Absent"],
        ["URLs sitemap",       str(r.get("sitemap_url_count", 0))],
    ]
    t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 23 — JWT Security
# ---------------------------------------------------------------------------
def _build_jwt_section(r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False) -> list:
    story = []
    story += _section_header(23, "Sécurité JWT", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-jwt).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    col_w = page_w - 4 * cm
    analyses = r.get("analyses", [])
    if not analyses:
        story.append(Paragraph(
            f"Tokens détectés : {r.get('tokens_found', 0)} — Aucune vulnérabilité JWT exposée.",
            styles["body"],
        ))
        return story

    head_style = ParagraphStyle("th23", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY)
    rows = [[Paragraph("Token (début)", head_style), Paragraph("Problèmes", head_style), Paragraph("Sévérité", head_style)]]
    for a in analyses:
        issues = ", ".join(a["issues"]) if a["issues"] else "OK"
        sev = a["severity"]
        sev_style = ParagraphStyle(
            "sv23",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_status_color(sev if sev in ("OK", "WARNING", "CRITICAL") else "WARNING"),
        )
        rows.append([a["token"][:40], issues, Paragraph(sev, sev_style)])

    t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.45, col_w * 0.20])
    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 24 — Recommandations
# ---------------------------------------------------------------------------
def _build_recommendations(
    ssl_result: dict[str, Any],
    headers_result: dict[str, Any],
    port_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    ports_skipped: bool = False,
    sca_result: dict[str, Any] | None = None,
    sca_skipped: bool = True,
) -> list:
    story = []
    story += _section_header(24, "Recommandations", styles)

    recommendations: list[tuple[str, str]] = []  # (priority, text)

    # SSL recommendations
    if ssl_result:
        ssl_status = ssl_result.get("status", "OK")
        tls_ok = ssl_result.get("tls_ok", True)
        if ssl_result.get("error") or ssl_status in ("CRITICAL", "WARNING"):
            recommendations.append(("CRITICAL", "Renouveler le certificat SSL via Let's Encrypt (certbot renew)"))
        if not tls_ok:
            recommendations.append(("WARNING", "Mettre à niveau vers TLS 1.2 minimum — désactiver TLS 1.0 et 1.1 dans la configuration serveur"))

    # Header recommendations
    if headers_result and not headers_result.get("error"):
        for header in headers_result.get("headers_missing", []):
            rec = HEADER_RECOMMENDATIONS.get(header)
            if rec:
                recommendations.append(("WARNING", rec))

    # SCA recommendations
    if not sca_skipped and sca_result and not sca_result.get("error"):
        for vuln in sca_result.get("vulns", []):
            sev = vuln.get("severity", "UNKNOWN")
            cve_str = ", ".join(vuln.get("cve_ids", ["N/A"]))
            recommendations.append((
                "CRITICAL" if sev in ("CRITICAL", "HIGH") else "WARNING",
                f"Mettre à jour {vuln['package']} ({vuln['version']}) — {cve_str} : {vuln['summary'][:120]}",
            ))

    # Port recommendations
    if not ports_skipped and port_result and not port_result.get("error"):
        critical_ports = port_result.get("critical_ports", [])
        if critical_ports:
            ports_str = ", ".join(
                f"{p} ({PORT_NAMES.get(p, 'unknown')})" for p in critical_ports
            )
            recommendations.append(
                ("CRITICAL", f"Fermer les ports {ports_str} exposés publiquement via pare-feu (ufw deny <port>)")
            )

    if not recommendations:
        story.append(Paragraph(
            "Aucune recommandation critique. Maintenez vos configurations à jour et effectuez des audits réguliers.",
            styles["body"],
        ))
        return story

    priority_order = {"CRITICAL": 0, "WARNING": 1, "OK": 2}
    recommendations.sort(key=lambda x: priority_order.get(x[0], 99))

    col_w = page_w - 4 * cm

    for priority, text in recommendations:
        c = _status_color(priority)
        priority_label = _status_bullet(priority)
        badge_style = ParagraphStyle(
            "pb24",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=c,
            alignment=TA_CENTER,
        )
        text_style = ParagraphStyle(
            "pt24",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_TEXT,
        )
        row_table = Table(
            [[Paragraph(priority_label, badge_style), Paragraph(text, text_style)]],
            colWidths=[2.5 * cm, col_w - 2.5 * cm],
        )
        row_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0),  COLOR_CARD),
            ("BACKGROUND",    (1, 0), (1, 0),  COLOR_BG),
            ("BOX",           (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("ALIGN",         (0, 0), (0, 0),  "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ]))
        story.append(row_table)
        story.append(Spacer(1, 0.2 * cm))

    return story


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_report(
    target_url: str,
    ssl_result: dict[str, Any],
    headers_result: dict[str, Any],
    port_result: dict[str, Any],
    output_path: str = "reports/rapport_audit.pdf",
    ports_skipped: bool = False,
    sca_result: dict[str, Any] | None = None,
    sca_skipped: bool = True,
    email_result: dict[str, Any] | None = None,
    email_skipped: bool = True,
    cookie_result: dict[str, Any] | None = None,
    cookie_skipped: bool = True,
    cors_result: dict[str, Any] | None = None,
    cors_skipped: bool = True,
    ip_result: dict[str, Any] | None = None,
    ip_skipped: bool = True,
    dns_result: dict[str, Any] | None = None,
    dns_skipped: bool = True,
    cms_result: dict[str, Any] | None = None,
    cms_skipped: bool = True,
    waf_result: dict[str, Any] | None = None,
    waf_skipped: bool = True,
    breach_result: dict[str, Any] | None = None,
    breach_skipped: bool = True,
    tech_result: dict[str, Any] | None = None,
    tech_skipped: bool = True,
    tls_result: dict[str, Any] | None = None,
    tls_skipped: bool = True,
    takeover_result: dict[str, Any] | None = None,
    takeover_skipped: bool = True,
    ti_result: dict[str, Any] | None = None,
    ti_skipped: bool = True,
    methods_result: dict[str, Any] | None = None,
    methods_skipped: bool = True,
    redirect_result: dict[str, Any] | None = None,
    redirect_skipped: bool = True,
    clickjacking_result: dict[str, Any] | None = None,
    clickjacking_skipped: bool = True,
    dirlist_result: dict[str, Any] | None = None,
    dirlist_skipped: bool = True,
    robots_result: dict[str, Any] | None = None,
    robots_skipped: bool = True,
    jwt_result: dict[str, Any] | None = None,
    jwt_skipped: bool = True,
) -> str:
    """
    Generate a professional PDF audit report.

    Args:
        target_url:     The scanned URL.
        ssl_result:     Dict returned by check_ssl().
        headers_result: Dict returned by check_headers().
        port_result:    Dict returned by scan_ports() or None/empty if skipped.
        output_path:    Destination file path (PDF).
        ports_skipped:  True when --skip-ports was used.
        sca_result:     Dict returned by check_sca() or None if skipped.
        sca_skipped:    True when SCA was not requested.

    Returns:
        The resolved output path where the PDF was written.
    """
    output_path = os.path.normpath(output_path)
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    report_date = datetime.now().strftime("%d/%m/%Y à %H:%M")
    page_w, page_h = A4

    doc = AuditDocTemplate(
        output_path,
        report_date=report_date,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,   # extra 0.5 cm for top band
        bottomMargin=2 * cm,
    )

    styles = _build_styles()

    # Compute statuses for summary
    statuses: dict[str, str] = {}
    if ssl_result:
        statuses["ssl"] = ssl_result.get("status", "CRITICAL")
    if headers_result:
        statuses["headers"] = headers_result.get("status", "CRITICAL")
    if not ports_skipped and port_result:
        statuses["ports"] = port_result.get("status", "OK")
    if not sca_skipped and sca_result:
        statuses["sca"] = sca_result.get("status", "OK")
    if not email_skipped and email_result:
        statuses["email"] = email_result.get("status", "OK")
    if not cookie_skipped and cookie_result:
        statuses["cookies"] = cookie_result.get("status", "OK")
    if not cors_skipped and cors_result:
        statuses["cors"] = cors_result.get("status", "OK")
    if not ip_skipped and ip_result:
        statuses["ip_rep"] = ip_result.get("status", "OK")
    if not dns_skipped and dns_result:
        statuses["dns"] = dns_result.get("status", "OK")
    if not cms_skipped and cms_result:
        statuses["cms"] = cms_result.get("status", "OK")
    if not waf_skipped and waf_result:
        statuses["waf"] = waf_result.get("status", "OK")
    if not breach_skipped and breach_result:
        statuses["breach"] = breach_result.get("status", "OK")
    if not tech_skipped and tech_result:
        statuses["tech"] = tech_result.get("status", "OK")
    if not tls_skipped and tls_result:
        statuses["tls"] = tls_result.get("status", "OK")
    if not takeover_skipped and takeover_result:
        statuses["takeover"] = takeover_result.get("status", "OK")
    if not ti_skipped and ti_result:
        statuses["threat_intel"] = ti_result.get("status", "OK")
    if not methods_skipped and methods_result:
        statuses["http_methods"] = methods_result.get("status", "OK")
    if not redirect_skipped and redirect_result:
        statuses["open_redirect"] = redirect_result.get("status", "OK")
    if not clickjacking_skipped and clickjacking_result:
        statuses["clickjacking"] = clickjacking_result.get("status", "OK")
    if not dirlist_skipped and dirlist_result:
        statuses["dir_listing"] = dirlist_result.get("status", "OK")
    if not robots_skipped and robots_result:
        statuses["robots"] = robots_result.get("status", "OK")
    if not jwt_skipped and jwt_result:
        statuses["jwt"] = jwt_result.get("status", "OK")

    all_status_values = list(statuses.values())
    if "CRITICAL" in all_status_values:
        overall = "CRITICAL"
    elif "WARNING" in all_status_values:
        overall = "WARNING"
    else:
        overall = "OK"

    usable_w = page_w - 4 * cm  # leftMargin + rightMargin = 4 cm

    story: list = []
    story += _build_cover(target_url, report_date, styles, usable_w, page_h, overall_status=overall)
    story += _build_toc(styles)
    story += _build_executive_summary(overall, statuses, styles, usable_w + 4 * cm)
    story += _build_ssl_section(ssl_result or {}, styles, usable_w + 4 * cm)
    story += _build_headers_section(headers_result or {}, styles, usable_w + 4 * cm)
    story += _build_ports_section(port_result or {}, styles, usable_w + 4 * cm, skipped=ports_skipped)
    story += _build_sca_section(sca_result or {}, styles, usable_w + 4 * cm, skipped=sca_skipped)
    story += _build_email_section(email_result or {}, styles, usable_w + 4 * cm, skipped=email_skipped)
    story += _build_cookie_section(cookie_result or {}, styles, usable_w + 4 * cm, skipped=cookie_skipped)
    story += _build_cors_section(cors_result or {}, styles, usable_w + 4 * cm, skipped=cors_skipped)
    story += _build_ip_reputation_section(ip_result or {}, styles, usable_w + 4 * cm, skipped=ip_skipped)
    story += _build_dns_section(dns_result or {}, styles, usable_w + 4 * cm, skipped=dns_skipped)
    story += _build_cms_section(cms_result or {}, styles, usable_w + 4 * cm, skipped=cms_skipped)
    story += _build_waf_section(waf_result or {}, styles, usable_w + 4 * cm, skipped=waf_skipped)
    story += _build_breach_section(breach_result or {}, styles, usable_w + 4 * cm, skipped=breach_skipped)
    story += _build_tech_section(tech_result or {}, styles, usable_w + 4 * cm, skipped=tech_skipped)
    story += _build_tls_section(tls_result or {}, styles, usable_w + 4 * cm, skipped=tls_skipped)
    story += _build_takeover_section(takeover_result or {}, styles, usable_w + 4 * cm, skipped=takeover_skipped)
    story += _build_threat_intel_section(ti_result or {}, styles, usable_w + 4 * cm, skipped=ti_skipped)
    story += _build_http_methods_section(methods_result or {}, styles, usable_w + 4 * cm, skipped=methods_skipped)
    story += _build_open_redirect_section(redirect_result or {}, styles, usable_w + 4 * cm, skipped=redirect_skipped)
    story += _build_clickjacking_section(clickjacking_result or {}, styles, usable_w + 4 * cm, skipped=clickjacking_skipped)
    story += _build_dirlist_section(dirlist_result or {}, styles, usable_w + 4 * cm, skipped=dirlist_skipped)
    story += _build_robots_section(robots_result or {}, styles, usable_w + 4 * cm, skipped=robots_skipped)
    story += _build_jwt_section(jwt_result or {}, styles, usable_w + 4 * cm, skipped=jwt_skipped)
    story += _build_recommendations(ssl_result or {}, headers_result or {}, port_result or {}, styles, usable_w + 4 * cm, ports_skipped=ports_skipped, sca_result=sca_result or {}, sca_skipped=sca_skipped)

    doc.build(story)
    return output_path
