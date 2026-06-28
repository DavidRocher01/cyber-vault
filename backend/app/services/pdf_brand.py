"""
pdf_brand.py — Shared visual identity for all CyberScan PDF reports.

Constants and helpers live here; the two large cover-page renderers have been
moved to pdf_covers.py and are re-exported below for backward compatibility.

Public API
----------
Constants  : DARK_BG, CARD_BG, BORDER, CYAN, GREEN, YELLOW, RED, ORANGE, GRAY, WHITE
             PAGE_W, PAGE_H, MARGIN, TOP_BAND, FOOTER_H
             DOC_COLOR
Functions  : score_color(pct)
             cat_score(cat_items, items)
             draw_page(canvas, doc, doc_type, title, subtitle)
             draw_compliance_cover(...)  — re-exported from pdf_covers
             draw_url_scan_cover(...)    — re-exported from pdf_covers
             section_rule(width, doc_type)
             get_styles(doc_type)
"""

from __future__ import annotations

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
DARK_BG = colors.HexColor("#0f172a")
CARD_BG = colors.HexColor("#1e293b")
HEADER_BG = colors.HexColor("#0c1a2e")
BORDER = colors.HexColor("#334155")
CYAN = colors.HexColor("#06b6d4")
GREEN = colors.HexColor("#4ade80")
YELLOW = colors.HexColor("#facc15")
RED = colors.HexColor("#f87171")
ORANGE = colors.HexColor("#fb923c")
GRAY = colors.HexColor("#94a3b8")
WHITE = colors.white

# Per-document-type accent colour
DOC_COLOR: dict[str, str] = {
    "nis2": "#8b5cf6",
    "iso27001": "#8b5cf6",
    "url": "#f97316",
    "scan": "#3b82f6",
    "test": "#10b981",
    "darkweb": "#ef4444",
    "phishing": "#f59e0b",
}

# Cover accent triples: (main, mid, dark-bg) hex strings
_COVER_ACCENT: dict[str, tuple[str, str, str]] = {
    "nis2": ("#8b5cf6", "#5b21b6", "#13102a"),
    "iso27001": ("#8b5cf6", "#5b21b6", "#13102a"),
    "url": ("#f97316", "#c2410c", "#1a0700"),
    "scan": ("#3b82f6", "#1d4ed8", "#0c1a2e"),
    "darkweb": ("#ef4444", "#b91c1c", "#1a0505"),
    "phishing": ("#f59e0b", "#b45309", "#1a1000"),
}

# Lighter header-title colour per doc type (right-zone text in band)
_BAND_TITLE_COLOR: dict[str, str] = {
    "nis2": "#c4b5fd",
    "iso27001": "#c4b5fd",
    "url": "#fed7aa",
    "scan": "#bae6fd",
    "darkweb": "#fca5a5",
    "phishing": "#fde68a",
}

# Short label shown in the band right zone for compliance covers
_BAND_COVER_LABEL: dict[str, str] = {
    "nis2": "DIRECTIVE NIS2",
    "iso27001": "ISO 27001:2022",
}

# Status badge styling (shared by compliance generators)
STATUS_COLOR = {"compliant": GREEN, "partial": YELLOW, "non_compliant": RED, "na": GRAY}
STATUS_LABEL = {
    "compliant": "Conforme",
    "partial": "Partiel",
    "non_compliant": "Non conforme",
    "na": "N/A",
}
STATUS_BG = {
    "compliant": colors.HexColor("#052e16"),
    "partial": colors.HexColor("#1c1400"),
    "non_compliant": colors.HexColor("#2d0a0a"),
    "na": colors.HexColor("#111827"),
}

# Layout constants
PAGE_W, PAGE_H = A4
MARGIN = 15  # mm (integer — multiply by `mm` to get points)
TOP_BAND = 14  # mm — content-page band height
FOOTER_H = 8  # mm — footer area height

SITE_EMAIL = "contact@cyberscanapp.com"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _accent_cols(doc_type: str) -> tuple:
    """Return (main, mid, bg) as Color objects for the given doc type."""
    if doc_type in _COVER_ACCENT:
        m, mid, bg = _COVER_ACCENT[doc_type]
        return colors.HexColor(m), colors.HexColor(mid), colors.HexColor(bg)
    h = DOC_COLOR.get(doc_type, "#06b6d4")
    return colors.HexColor(h), colors.HexColor(h), DARK_BG


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def score_color(pct: int):
    """Return GREEN / YELLOW / RED based on score percentage."""
    if pct >= 80:
        return GREEN
    if pct >= 50:
        return YELLOW
    return RED


def cat_score(cat_items: list, items: dict) -> int:
    """Compute a category compliance score as a 0-100 integer."""
    scorable = [it for it in cat_items if items.get(it["id"], "non_compliant") != "na"]
    if not scorable:
        return 0
    pts = sum(
        2
        if items.get(it["id"], "non_compliant") == "compliant"
        else 1
        if items.get(it["id"], "non_compliant") == "partial"
        else 0
        for it in scorable
    )
    return round(pts / (len(scorable) * 2) * 100)


# ---------------------------------------------------------------------------
# Shared band drawing helper (used by draw_page and cover renderers)
# ---------------------------------------------------------------------------


def _draw_band(
    canvas,
    *,
    band_y: float,
    band_h: float,
    band_cy: float,
    doc_type: str,
    doc_color,
    right_text: str,
    right_sub: str,
) -> None:
    """Draw the top accent band (flat dark bg, stripe, logo, wordmark, right text)."""
    M = MARGIN * mm
    W = PAGE_W

    # Band background
    canvas.setFillColor(colors.HexColor("#0f0a28"))
    canvas.rect(0, band_y, W, band_h, fill=1, stroke=0)

    # Left stripe (2 mm)
    canvas.setFillColor(doc_color)
    canvas.rect(0, band_y, 2 * mm, band_h, fill=1, stroke=0)

    # Bottom border
    canvas.setStrokeColor(doc_color)
    canvas.setLineWidth(2.5)
    canvas.line(0, band_y, W, band_y)

    # Circle logo "CS"
    logo_cx = M + 5 * mm
    logo_r = band_h * 0.22
    canvas.setFillColor(CYAN)
    canvas.circle(logo_cx, band_cy, logo_r, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#22d3ee"))
    canvas.circle(
        logo_cx - logo_r * 0.14,
        band_cy + logo_r * 0.14,
        logo_r * 0.55,
        fill=1,
        stroke=0,
    )
    canvas.setFillColor(colors.HexColor("#083344"))
    canvas.setFont("Helvetica-Bold", band_h * 0.33)
    canvas.drawCentredString(logo_cx, band_cy - band_h * 0.07, "CS")

    # "CyberScan" wordmark
    wm_x = logo_cx + logo_r + 2.5 * mm
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", band_h * 0.62)
    canvas.drawString(wm_x, band_cy - band_h * 0.12, "CyberScan")

    # Thin rule connecting wordmark to right text
    rule_x0 = wm_x + 52
    rule_x1 = W - M - 45 * mm
    if rule_x1 > rule_x0 + 8:
        canvas.setStrokeColor(colors.HexColor("#2d1b69"))
        canvas.setLineWidth(0.5)
        canvas.line(rule_x0 + 2 * mm, band_cy, rule_x1 - 2 * mm, band_cy)

    # Right zone: stacked title + sub
    right_col = colors.HexColor(_BAND_TITLE_COLOR.get(doc_type, "#e2e8f0"))
    canvas.setFillColor(right_col)
    canvas.setFont("Helvetica-Bold", band_h * 0.50)
    canvas.drawRightString(W - M, band_cy + band_h * 0.10, right_text)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica", band_h * 0.38)
    canvas.drawRightString(W - M, band_cy - band_h * 0.28, right_sub)


# ---------------------------------------------------------------------------
# Content-page template
# ---------------------------------------------------------------------------


def draw_page(canvas, doc, doc_type: str, title: str, subtitle: str = "") -> None:
    """
    Render the common dark page background, top band, and footer.
    Call as onFirstPage / onLaterPages in SimpleDocTemplate.build().
    """
    doc_color = colors.HexColor(DOC_COLOR.get(doc_type, "#06b6d4"))
    today_str = datetime.now().strftime("%d/%m/%Y")
    M = MARGIN * mm
    BAND_H = TOP_BAND * mm
    band_y = PAGE_H - BAND_H
    band_cy = PAGE_H - BAND_H / 2

    canvas.saveState()

    # Full-page dark background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    _draw_band(
        canvas,
        band_y=band_y,
        band_h=BAND_H,
        band_cy=band_cy,
        doc_type=doc_type,
        doc_color=doc_color,
        right_text=title.upper(),
        right_sub=today_str,
    )

    # Footer
    footer_y = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, footer_y, PAGE_W - M, footer_y)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, footer_y - 5 * mm, "CyberScan — confidentiel")
    canvas.drawCentredString(PAGE_W / 2, footer_y - 5 * mm, f"Page {doc.page}")
    canvas.drawRightString(PAGE_W - M, footer_y - 5 * mm, today_str)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Cover-page renderers — moved to pdf_covers.py, re-exported for compat
# ---------------------------------------------------------------------------
# These imports must come AFTER all constants above are defined (pdf_covers
# imports from this module).
from app.services.pdf_covers import (  # noqa: E402, F401
    draw_compliance_cover,
    draw_url_scan_cover,
)

# ---------------------------------------------------------------------------
# Section rule helper
# ---------------------------------------------------------------------------


def section_rule(width, doc_type: str) -> HRFlowable:
    """Return a coloured HRFlowable matching the document type."""
    hex_color = DOC_COLOR.get(doc_type, "#06b6d4")
    base = colors.HexColor(hex_color)
    r, g, b = base.red, base.green, base.blue
    bg_r, bg_g, bg_b = DARK_BG.red, DARK_BG.green, DARK_BG.blue
    alpha = 0.6
    blended = colors.Color(
        r * alpha + bg_r * (1 - alpha),
        g * alpha + bg_g * (1 - alpha),
        b * alpha + bg_b * (1 - alpha),
    )
    return HRFlowable(width=width, thickness=0.8, color=blended, spaceAfter=4, spaceBefore=2)


# ---------------------------------------------------------------------------
# Shared paragraph styles
# ---------------------------------------------------------------------------


def get_styles(doc_type: str) -> dict[str, ParagraphStyle]:
    doc_hex = DOC_COLOR.get(doc_type, "#06b6d4")
    doc_color = colors.HexColor(doc_hex)

    def _s(name: str, **kw) -> ParagraphStyle:
        defaults = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    return {
        "title": _s(
            f"brand_title_{doc_type}",
            fontSize=20,
            fontName="Helvetica-Bold",
            textColor=WHITE,
        ),
        "subtitle": _s(f"brand_subtitle_{doc_type}", fontSize=10, textColor=GRAY),
        "section": _s(
            f"brand_section_{doc_type}",
            fontSize=12,
            fontName="Helvetica-Bold",
            textColor=doc_color,
            spaceBefore=12,
            spaceAfter=4,
        ),
        "subsection": _s(
            f"brand_subsection_{doc_type}",
            fontSize=10,
            fontName="Helvetica-Bold",
            textColor=WHITE,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "body": _s(f"brand_body_{doc_type}", fontSize=9, textColor=colors.HexColor("#cbd5e1")),
        "small": _s(f"brand_small_{doc_type}", fontSize=7, textColor=GRAY),
        "mono": _s(f"brand_mono_{doc_type}", fontSize=8, fontName="Courier", textColor=CYAN),
        "label": _s(
            f"brand_label_{doc_type}",
            fontSize=9,
            fontName="Helvetica-Bold",
            textColor=WHITE,
        ),
        "badge_pass": _s(
            f"brand_badge_pass_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=GREEN,
        ),
        "badge_fail": _s(
            f"brand_badge_fail_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=RED,
        ),
        "badge_warn": _s(
            f"brand_badge_warn_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=YELLOW,
        ),
        "badge_gray": _s(
            f"brand_badge_gray_{doc_type}",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=GRAY,
        ),
    }
