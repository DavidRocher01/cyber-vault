"""
pdf_brand.py — Shared visual identity for all CyberScan PDF reports.

Public API
----------
Constants  : DARK_BG, CARD_BG, BORDER, CYAN, GREEN, YELLOW, RED, ORANGE, GRAY, WHITE
             PAGE_W, PAGE_H, MARGIN, TOP_BAND, FOOTER_H
             DOC_COLOR
Functions  : score_color(pct)
             cat_score(cat_items, items)
             draw_page(canvas, doc, doc_type, title, subtitle)
             draw_compliance_cover(canvas, doc, *, doc_type, title_line1, title_line2,
                                   score, score_label, total, compliant, partial,
                                   nc, na, date_str, domain_scores)
             draw_url_scan_cover(canvas, doc, *, url, verdict_label, verdict_color_hex,
                                  threat_score, findings_count, redirect_count,
                                  ssl_valid, date_str)
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
DARK_BG   = colors.HexColor("#0f172a")
CARD_BG   = colors.HexColor("#1e293b")
HEADER_BG = colors.HexColor("#0c1a2e")
BORDER    = colors.HexColor("#334155")
CYAN      = colors.HexColor("#06b6d4")
GREEN     = colors.HexColor("#4ade80")
YELLOW    = colors.HexColor("#facc15")
RED       = colors.HexColor("#f87171")
ORANGE    = colors.HexColor("#fb923c")
GRAY      = colors.HexColor("#94a3b8")
WHITE     = colors.white

# Per-document-type accent colour
DOC_COLOR: dict[str, str] = {
    "nis2":     "#8b5cf6",
    "iso27001": "#8b5cf6",
    "url":      "#f97316",
    "scan":     "#3b82f6",
    "test":     "#10b981",
}

# Cover accent triples: (main, mid, dark-bg) hex strings
_COVER_ACCENT: dict[str, tuple[str, str, str]] = {
    "nis2":     ("#8b5cf6", "#5b21b6", "#13102a"),
    "iso27001": ("#8b5cf6", "#5b21b6", "#13102a"),
    "url":      ("#f97316", "#c2410c", "#1a0700"),
    "scan":     ("#3b82f6", "#1d4ed8", "#0c1a2e"),
}

# Lighter header-title colour per doc type (right-zone text in band)
_BAND_TITLE_COLOR: dict[str, str] = {
    "nis2":     "#c4b5fd",
    "iso27001": "#c4b5fd",
    "url":      "#fed7aa",
    "scan":     "#bae6fd",
}

# Short label shown in the band right zone for compliance covers
_BAND_COVER_LABEL: dict[str, str] = {
    "nis2":     "DIRECTIVE NIS2",
    "iso27001": "ISO 27001:2022",
}

# Status badge styling (shared by compliance generators)
STATUS_COLOR = {"compliant": GREEN, "partial": YELLOW, "non_compliant": RED, "na": GRAY}
STATUS_LABEL = {"compliant": "Conforme", "partial": "Partiel",
                "non_compliant": "Non conforme", "na": "N/A"}
STATUS_BG    = {
    "compliant":     colors.HexColor("#052e16"),
    "partial":       colors.HexColor("#1c1400"),
    "non_compliant": colors.HexColor("#2d0a0a"),
    "na":            colors.HexColor("#111827"),
}

# Layout constants
PAGE_W, PAGE_H = A4
MARGIN   = 15    # mm (integer — multiply by `mm` to get points)
TOP_BAND = 14    # mm — content-page band height
FOOTER_H = 8     # mm — footer area height

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
    if pct >= 80: return GREEN
    if pct >= 50: return YELLOW
    return RED


def cat_score(cat_items: list, items: dict) -> int:
    """Compute a category compliance score as a 0–100 integer."""
    scorable = [it for it in cat_items if items.get(it["id"], "non_compliant") != "na"]
    if not scorable:
        return 0
    pts = sum(
        2 if items.get(it["id"], "non_compliant") == "compliant"
        else 1 if items.get(it["id"], "non_compliant") == "partial" else 0
        for it in scorable
    )
    return round(pts / (len(scorable) * 2) * 100)


# ---------------------------------------------------------------------------
# Shared band drawing helper (used by both draw_page and draw_compliance_cover)
# ---------------------------------------------------------------------------

def _draw_band(canvas, *, band_y: float, band_h: float,
               band_cy: float, doc_type: str, doc_color,
               right_text: str, right_sub: str) -> None:
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
    logo_r  = band_h * 0.22
    canvas.setFillColor(CYAN)
    canvas.circle(logo_cx, band_cy, logo_r, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#22d3ee"))
    canvas.circle(logo_cx - logo_r * 0.14, band_cy + logo_r * 0.14,
                  logo_r * 0.55, fill=1, stroke=0)
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
    M         = MARGIN * mm
    BAND_H    = TOP_BAND * mm
    band_y    = PAGE_H - BAND_H
    band_cy   = PAGE_H - BAND_H / 2

    canvas.saveState()

    # Full-page dark background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    _draw_band(canvas,
               band_y=band_y, band_h=BAND_H, band_cy=band_cy,
               doc_type=doc_type, doc_color=doc_color,
               right_text=title.upper(),
               right_sub=today_str)

    # Footer
    footer_y = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, footer_y, PAGE_W - M, footer_y)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, footer_y - 5 * mm, "CyberScan \u2014 confidentiel")
    canvas.drawCentredString(PAGE_W / 2, footer_y - 5 * mm, f"Page {doc.page}")
    canvas.drawRightString(PAGE_W - M, footer_y - 5 * mm, today_str)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Compliance cover page (NIS2 / ISO 27001)
# ---------------------------------------------------------------------------

def draw_compliance_cover(
    canvas, doc, *,
    doc_type: str,
    title_line1: str,
    title_line2: str,
    score: int,
    score_label: str,
    total: int,
    compliant: int,
    partial: int,
    nc: int,
    na: int,
    date_str: str,
    domain_scores: list[tuple[str, int]],
) -> None:
    """Full cover page for compliance-type PDFs (NIS2, ISO 27001)."""
    W, H   = PAGE_W, PAGE_H
    M      = MARGIN * mm
    sc     = score_color(score)
    col, col_mid, col_bg = _accent_cols(doc_type)

    BAND_H  = 18 * mm
    band_y  = H - BAND_H
    band_cy = H - BAND_H / 2

    canvas.saveState()

    # Background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # Band
    band_label = _BAND_COVER_LABEL.get(doc_type, title_line2.upper())
    _draw_band(canvas,
               band_y=band_y, band_h=BAND_H, band_cy=band_cy,
               doc_type=doc_type, doc_color=col,
               right_text=band_label,
               right_sub=date_str[:10])

    # ── Title block ───────────────────────────────────────────────────────────
    acc_y = H - 56 * mm
    canvas.setFillColor(col_mid)
    canvas.roundRect(M, acc_y, 3 * mm, 22 * mm, radius=1 * mm, fill=1, stroke=0)

    tx = M + 7 * mm
    ty = H - 26 * mm

    canvas.setFillColor(col)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(tx, ty, title_line1)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(tx, ty - 9 * mm, title_line2)

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(tx, ty - 16 * mm,
                      f"Genere le {date_str}  \u2022  {SITE_EMAIL}")

    # ── Score card ────────────────────────────────────────────────────────────
    card_y = H - 120 * mm
    card_h = 68 * mm
    card_w = W - 2 * M
    left_w  = card_w * 0.40
    right_w = card_w * 0.60

    canvas.setFillColor(col)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(M, card_y + card_h + 4 * mm, "SYNTHESE DE CONFORMITE")

    canvas.setFillColor(colors.HexColor("#111c30"))
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#1e2d4a"))
    canvas.setLineWidth(0.8)
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=0, stroke=1)
    # Top stripe — thick line contained within card's rounded corners
    canvas.setStrokeColor(col_mid)
    canvas.setLineWidth(2 * mm)
    canvas.setLineCap(0)
    canvas.line(M + 4 * mm, card_y + card_h - 1 * mm,
                M + card_w - 4 * mm, card_y + card_h - 1 * mm)

    # Gauge (left 40%)
    cx = M + left_w / 2
    cy = card_y + card_h / 2 + 5 * mm
    r  = 20 * mm

    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(13)
    canvas.setLineCap(0)
    p = canvas.beginPath()
    p.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)
    canvas.drawPath(p, stroke=1, fill=0)

    if score > 0:
        fill_extent = min(score / 100 * 180, 180)
        canvas.setStrokeColor(sc)
        canvas.setLineWidth(13)
        canvas.setLineCap(0)
        p2 = canvas.beginPath()
        p2.arc(cx - r, cy - r, cx + r, cy + r,
               startAng=180 - fill_extent, extent=fill_extent)
        canvas.drawPath(p2, stroke=1, fill=0)

    canvas.setFillColor(colors.HexColor("#141e30"))
    canvas.circle(cx, cy, r - 7 * mm, fill=1, stroke=0)
    canvas.setFillColor(sc)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawCentredString(cx, cy - 4 * mm, f"{score}%")
    canvas.setFillColor(sc)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(cx, card_y + 11 * mm, score_label)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(cx, card_y + 5.5 * mm, f"{total} controles")

    sep_x = M + left_w + 4 * mm
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(0.8)
    canvas.line(sep_x, card_y + 8 * mm, sep_x, card_y + card_h - 8 * mm)

    # KPI 2×2 grid (right 60%)
    kpis = [
        (compliant, "Conformes",  GREEN,  colors.HexColor("#052e16")),
        (partial,   "Partiels",   YELLOW, colors.HexColor("#1c1400")),
        (nc,        "Non conf.",  RED,    colors.HexColor("#2d0a0a")),
        (na,        "N/A",        GRAY,   colors.HexColor("#111827")),
    ]
    gx0    = M + left_w + 8 * mm
    gw     = right_w - 12 * mm
    cell_w = gw / 2 - 2 * mm
    cell_h = card_h / 2 - 5 * mm

    for i, (val, lbl, k_col, bg) in enumerate(kpis):
        kx = gx0 + (i % 2) * (cell_w + 4 * mm)
        ky = card_y + card_h - (i // 2 + 1) * (cell_h + 4 * mm) + 2 * mm
        canvas.setFillColor(bg)
        canvas.roundRect(kx, ky, cell_w, cell_h, radius=2.5 * mm, fill=1, stroke=0)
        # Top stripe — contained within rounded corners
        canvas.setStrokeColor(k_col)
        canvas.setLineWidth(2 * mm)
        canvas.setLineCap(0)
        canvas.line(kx + 2.5 * mm, ky + cell_h - 1 * mm,
                    kx + cell_w - 2.5 * mm, ky + cell_h - 1 * mm)
        canvas.setFillColor(k_col)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(kx + cell_w / 2, ky + cell_h * 0.52, str(val))
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(kx + cell_w / 2, ky + 3.5 * mm, lbl)

    # ── Domain scores grid ────────────────────────────────────────────────────
    dom_available = card_y - 8 * mm - 20 * mm
    num_dom = len(domain_scores)
    ncols   = 2
    nrows   = (num_dom + ncols - 1) // ncols
    dom_top = card_y - 8 * mm
    gap_h   = 3 * mm
    row_h   = (dom_available - gap_h) / max(nrows, 1)
    col_gap = 4 * mm
    col_w   = (card_w - col_gap) / ncols

    canvas.setFillColor(col)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(M, dom_top, "RESULTATS PAR DOMAINE")

    for idx, (lbl, pct) in enumerate(domain_scores):
        col_i  = idx % ncols
        row_i  = idx // ncols
        dx     = M + col_i * (col_w + col_gap)
        cell_y = dom_top - (row_i + 1) * row_h - row_i * gap_h + gap_h
        cell_h = row_h - gap_h
        d_col  = score_color(pct)

        canvas.setFillColor(colors.HexColor("#0e1623"))
        canvas.roundRect(dx, cell_y, col_w, cell_h, radius=2 * mm, fill=1, stroke=0)

        # Left accent — thick line contained within rounded corners
        r_cell = 2 * mm
        canvas.setStrokeColor(d_col)
        canvas.setLineWidth(4 * mm)
        canvas.setLineCap(0)
        canvas.line(dx + 2 * mm, cell_y + r_cell,
                    dx + 2 * mm, cell_y + cell_h - r_cell)

        inner_x = dx + 7 * mm
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 7.5)
        short_lbl = lbl if len(lbl) <= 26 else lbl[:25] + "\u2026"
        canvas.drawString(inner_x, cell_y + cell_h * 0.55, short_lbl)

        bar_x   = inner_x
        bar_y   = cell_y + cell_h * 0.18
        bar_w   = col_w - inner_x + dx - 12 * mm
        bar_h_v = 3.5 * mm
        canvas.setFillColor(colors.HexColor("#1e293b"))
        canvas.roundRect(bar_x, bar_y, bar_w, bar_h_v, radius=1 * mm, fill=1, stroke=0)
        if pct > 0:
            canvas.setFillColor(d_col)
            canvas.roundRect(bar_x, bar_y, max(bar_w * pct / 100, 2 * mm), bar_h_v,
                             radius=1 * mm, fill=1, stroke=0)

        canvas.setFillColor(d_col)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(dx + col_w - 3 * mm, cell_y + cell_h * 0.38, f"{pct}%")

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, footer_y + 4 * mm, W - M, footer_y + 4 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, footer_y - 1 * mm, "CyberScan \u2014 confidentiel")
    canvas.drawCentredString(W / 2, footer_y - 1 * mm, "Page 1")
    canvas.drawRightString(W - M, footer_y - 1 * mm, date_str[:10])

    canvas.restoreState()


# ---------------------------------------------------------------------------
# URL scan cover page
# ---------------------------------------------------------------------------

def draw_url_scan_cover(
    canvas, doc, *,
    url: str,
    verdict_label: str,
    verdict_color_hex: str,
    threat_score: int,
    findings_count: int,
    redirect_count: int,
    ssl_valid: bool,
    date_str: str,
) -> None:
    """Full cover page for URL scan reports."""
    W, H  = PAGE_W, PAGE_H
    M     = MARGIN * mm
    v_col = colors.HexColor(verdict_color_hex)
    col, col_mid, col_bg = _accent_cols("url")

    BAND_H  = 18 * mm
    band_y  = H - BAND_H
    band_cy = H - BAND_H / 2

    canvas.saveState()

    # Background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # Band
    _draw_band(canvas,
               band_y=band_y, band_h=BAND_H, band_cy=band_cy,
               doc_type="url", doc_color=col,
               right_text="RAPPORT D'ANALYSE D'URL",
               right_sub=date_str[:10])

    # ── Title block ───────────────────────────────────────────────────────────
    acc_y = H - 56 * mm
    canvas.setFillColor(col_mid)
    canvas.roundRect(M, acc_y, 3 * mm, 22 * mm, radius=1 * mm, fill=1, stroke=0)

    tx = M + 7 * mm
    ty = H - 26 * mm

    canvas.setFillColor(col)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(tx, ty, "Rapport d'analyse")

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(tx, ty - 9 * mm, "Analyse d'URL")

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(tx, ty - 16 * mm,
                      f"Genere le {date_str}  \u2022  {SITE_EMAIL}")

    # ── Verdict card ──────────────────────────────────────────────────────────
    card_y = H - 125 * mm
    card_h = 65 * mm
    card_w = W - 2 * M

    canvas.setFillColor(col)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(M, card_y + card_h + 4 * mm, "RESULTAT DE L'ANALYSE")

    canvas.setFillColor(colors.HexColor("#111c30"))
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#1e2d4a"))
    canvas.setLineWidth(0.8)
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=0, stroke=1)
    # Top stripe — contained within card's rounded corners
    canvas.setStrokeColor(col_mid)
    canvas.setLineWidth(2 * mm)
    canvas.setLineCap(0)
    canvas.line(M + 4 * mm, card_y + card_h - 1 * mm,
                M + card_w - 4 * mm, card_y + card_h - 1 * mm)

    # Verdict (left 45%)
    left_w  = card_w * 0.45
    right_w = card_w * 0.55
    vcx     = M + left_w / 2
    vcy     = card_y + card_h / 2 + 4 * mm

    # Verdict circle background
    canvas.setFillColor(colors.HexColor("#1e293b"))
    canvas.circle(vcx, vcy, 18 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(v_col)
    canvas.setLineWidth(2.5)
    canvas.circle(vcx, vcy, 18 * mm, fill=0, stroke=1)

    canvas.setFillColor(v_col)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(vcx, vcy - 1.5 * mm, verdict_label)

    # Threat score below
    canvas.setFillColor(v_col)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawCentredString(vcx, card_y + 11 * mm, f"Score: {threat_score}/100")
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(vcx, card_y + 5.5 * mm, "Indice de menace")

    # Separator
    sep_x = M + left_w + 4 * mm
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(0.8)
    canvas.line(sep_x, card_y + 8 * mm, sep_x, card_y + card_h - 8 * mm)

    # KPI row (right side, 3 cells)
    kpis = [
        (str(findings_count), "Alertes",   RED   if findings_count > 0 else GREEN),
        (str(redirect_count), "Redirects", YELLOW if redirect_count > 0 else GREEN),
        ("\u2713 SSL" if ssl_valid else "\u2717 SSL",
         "Certificat",                     GREEN  if ssl_valid else RED),
    ]
    gx0    = sep_x + 4 * mm
    gw     = right_w - 12 * mm
    cell_w = gw / 3 - 2 * mm
    cell_h = card_h - 14 * mm

    for i, (val, lbl, k_col) in enumerate(kpis):
        kx = gx0 + i * (cell_w + 3 * mm)
        ky = card_y + 7 * mm
        canvas.setFillColor(colors.HexColor("#1e293b"))
        canvas.roundRect(kx, ky, cell_w, cell_h, radius=2.5 * mm, fill=1, stroke=0)
        # Top stripe — contained within rounded corners
        canvas.setStrokeColor(k_col)
        canvas.setLineWidth(2 * mm)
        canvas.setLineCap(0)
        canvas.line(kx + 2.5 * mm, ky + cell_h - 1 * mm,
                    kx + cell_w - 2.5 * mm, ky + cell_h - 1 * mm)
        canvas.setFillColor(k_col)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawCentredString(kx + cell_w / 2, ky + cell_h * 0.52, val)
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(kx + cell_w / 2, ky + 3.5 * mm, lbl)

    # ── URL analysée ──────────────────────────────────────────────────────────
    url_y = card_y - 12 * mm
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(M, url_y + 2 * mm, "URL ANALYSEE")

    canvas.setFillColor(colors.HexColor("#0e1623"))
    canvas.roundRect(M, url_y - 8 * mm, card_w, 9 * mm, radius=2 * mm, fill=1, stroke=0)

    max_url = 90
    short_url = url if len(url) <= max_url else url[:max_url - 1] + "\u2026"
    canvas.setFillColor(CYAN)
    canvas.setFont("Courier", 8)
    canvas.drawString(M + 4 * mm, url_y - 3.5 * mm, short_url)

    # ── Footer ────────────────────────────────────────────────────────────────
    footer_y = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, footer_y + 4 * mm, W - M, footer_y + 4 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, footer_y - 1 * mm, "CyberScan \u2014 confidentiel")
    canvas.drawCentredString(W / 2, footer_y - 1 * mm, "Page 1")
    canvas.drawRightString(W - M, footer_y - 1 * mm, date_str[:10])

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Section rule helper
# ---------------------------------------------------------------------------

def section_rule(width, doc_type: str) -> HRFlowable:
    """Return a coloured HRFlowable matching the document type."""
    hex_color = DOC_COLOR.get(doc_type, "#06b6d4")
    base      = colors.HexColor(hex_color)
    r, g, b   = base.red, base.green, base.blue
    bg_r, bg_g, bg_b = DARK_BG.red, DARK_BG.green, DARK_BG.blue
    alpha   = 0.6
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
    doc_hex   = DOC_COLOR.get(doc_type, "#06b6d4")
    doc_color = colors.HexColor(doc_hex)

    def _s(name: str, **kw) -> ParagraphStyle:
        defaults = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2)
        defaults.update(kw)
        return ParagraphStyle(name, **defaults)

    return {
        "title": _s(f"brand_title_{doc_type}", fontSize=20,
                    fontName="Helvetica-Bold", textColor=WHITE),
        "subtitle": _s(f"brand_subtitle_{doc_type}", fontSize=10, textColor=GRAY),
        "section": _s(f"brand_section_{doc_type}", fontSize=12,
                      fontName="Helvetica-Bold", textColor=doc_color,
                      spaceBefore=12, spaceAfter=4),
        "subsection": _s(f"brand_subsection_{doc_type}", fontSize=10,
                         fontName="Helvetica-Bold", textColor=WHITE,
                         spaceBefore=8, spaceAfter=3),
        "body": _s(f"brand_body_{doc_type}", fontSize=9,
                   textColor=colors.HexColor("#cbd5e1")),
        "small": _s(f"brand_small_{doc_type}", fontSize=7, textColor=GRAY),
        "mono": _s(f"brand_mono_{doc_type}", fontSize=8,
                   fontName="Courier", textColor=CYAN),
        "label": _s(f"brand_label_{doc_type}", fontSize=9,
                    fontName="Helvetica-Bold", textColor=WHITE),
        "badge_pass": _s(f"brand_badge_pass_{doc_type}", fontSize=8,
                         fontName="Helvetica-Bold", textColor=GREEN),
        "badge_fail": _s(f"brand_badge_fail_{doc_type}", fontSize=8,
                         fontName="Helvetica-Bold", textColor=RED),
        "badge_warn": _s(f"brand_badge_warn_{doc_type}", fontSize=8,
                         fontName="Helvetica-Bold", textColor=YELLOW),
        "badge_gray": _s(f"brand_badge_gray_{doc_type}", fontSize=8,
                         fontName="Helvetica-Bold", textColor=GRAY),
    }
