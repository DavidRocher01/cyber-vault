"""
pdf_brand.py
============
Shared visual identity for all CyberScan PDF reports.

Provides:
  - Colour palette constants
  - draw_page()   — onFirstPage / onLaterPages callback
  - section_rule() — coloured HRFlowable
  - get_styles()  — common ParagraphStyle dict
  - Layout constants (PAGE_W, PAGE_H, MARGIN, TOP_BAND, FOOTER_H)
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
DARK_BG   = colors.HexColor("#0f172a")   # page background
CARD_BG   = colors.HexColor("#1e293b")   # card / table background
HEADER_BG = colors.HexColor("#0c1a2e")   # top-band background
BORDER    = colors.HexColor("#334155")   # borders
CYAN      = colors.HexColor("#06b6d4")   # primary accent
GREEN     = colors.HexColor("#4ade80")
YELLOW    = colors.HexColor("#facc15")
RED       = colors.HexColor("#f87171")
ORANGE    = colors.HexColor("#fb923c")
GRAY      = colors.HexColor("#94a3b8")
WHITE     = colors.white

# Per-document-type badge colour
DOC_COLOR: dict[str, str] = {
    "nis2": "#8b5cf6",   # violet
    "url":  "#f97316",   # orange
    "scan": "#3b82f6",   # blue
    "test": "#10b981",   # emerald green
}

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
PAGE_W, PAGE_H = A4
MARGIN   = 15       # mm — left/right margin
TOP_BAND = 10       # mm — top header band height
FOOTER_H = 8        # mm — footer band height


# ---------------------------------------------------------------------------
# Page template callback
# ---------------------------------------------------------------------------
def draw_page(
    canvas,
    doc,
    doc_type: str,
    title: str,
    subtitle: str = "",
) -> None:
    """
    Render the common dark page background, top band, and footer.
    Call as ``onFirstPage`` / ``onLaterPages`` in SimpleDocTemplate.build().

    Example::

        doc.build(
            story,
            onFirstPage=lambda c, d: draw_page(c, d, "nis2", "Conformité NIS2", user_email),
            onLaterPages=lambda c, d: draw_page(c, d, "nis2", "Conformité NIS2"),
        )
    """
    doc_hex   = DOC_COLOR.get(doc_type, "#06b6d4")
    doc_color = colors.HexColor(doc_hex)
    today_str = datetime.now().strftime("%d/%m/%Y")

    canvas.saveState()

    # ── Full-page dark background ─────────────────────────────────────────────
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ── Top band ──────────────────────────────────────────────────────────────
    band_y = PAGE_H - TOP_BAND * mm
    band_h = TOP_BAND * mm

    # Band background (doc colour at 30 % opacity)
    r, g, b = doc_color.red, doc_color.green, doc_color.blue
    canvas.setFillColorRGB(r, g, b, alpha=0.30)
    canvas.rect(0, band_y, PAGE_W, band_h, fill=1, stroke=0)

    # Top edge line (2 px, full doc colour)
    canvas.setStrokeColor(doc_color)
    canvas.setLineWidth(2)
    canvas.line(0, PAGE_H - 1, PAGE_W, PAGE_H - 1)

    # "CS" logo mark — small cyan rounded square on the left
    logo_size = 6 * mm
    logo_x    = MARGIN * mm
    logo_y    = band_y + (band_h - logo_size) / 2
    canvas.setFillColor(CYAN)
    canvas.roundRect(logo_x, logo_y, logo_size, logo_size, radius=1.5 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 6)
    canvas.drawCentredString(logo_x + logo_size / 2, logo_y + 1.5 * mm, "CS")

    # "CyberScan" text
    text_x = logo_x + logo_size + 3 * mm
    mid_y  = band_y + band_h / 2 - 1.5 * mm
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(text_x, mid_y, "CyberScan")

    # Separator pipe
    sep_x = text_x + 60
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(sep_x, mid_y, "|")

    # Document title
    canvas.setFillColor(doc_color)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(sep_x + 8, mid_y, title)

    # Subtitle (e.g. user e-mail on first page)
    if subtitle:
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(sep_x + 8, mid_y - 8, subtitle)

    # Date — right-aligned
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - MARGIN * mm, mid_y, today_str)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = FOOTER_H * mm

    # Separator line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN * mm, footer_y, PAGE_W - MARGIN * mm, footer_y)

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)

    # Left: confidentiality notice
    canvas.drawString(MARGIN * mm, footer_y - 5 * mm, "CyberScan \u2014 confidentiel")

    # Centre: page number
    canvas.drawCentredString(
        PAGE_W / 2,
        footer_y - 5 * mm,
        f"Page {doc.page}",
    )

    # Right: date
    canvas.drawRightString(PAGE_W - MARGIN * mm, footer_y - 5 * mm, today_str)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Section rule helper
# ---------------------------------------------------------------------------
def section_rule(width, doc_type: str) -> HRFlowable:
    """Return a coloured HRFlowable matching the document type (60 % opacity)."""
    hex_color = DOC_COLOR.get(doc_type, "#06b6d4")
    base      = colors.HexColor(hex_color)
    r, g, b   = base.red, base.green, base.blue
    # Build a blended colour over DARK_BG (approximation — alpha 0.6 on DARK_BG)
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
    """Return a dict of common ParagraphStyles keyed by role name."""
    doc_hex   = DOC_COLOR.get(doc_type, "#06b6d4")
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
        "subtitle": _s(
            f"brand_subtitle_{doc_type}",
            fontSize=10,
            textColor=GRAY,
        ),
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
        "body": _s(
            f"brand_body_{doc_type}",
            fontSize=9,
            textColor=colors.HexColor("#cbd5e1"),
        ),
        "small": _s(
            f"brand_small_{doc_type}",
            fontSize=7,
            textColor=GRAY,
        ),
        "mono": _s(
            f"brand_mono_{doc_type}",
            fontSize=8,
            fontName="Courier",
            textColor=CYAN,
        ),
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
