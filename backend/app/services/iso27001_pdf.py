"""
ISO 27001:2022 Compliance PDF — premium visual design.
Cover page drawn directly on canvas. Tables for summary + detail.
"""
from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle, KeepTogether, PageBreak,
)

from app.services.pdf_brand import (
    BORDER, CARD_BG, CYAN, DARK_BG, GRAY, GREEN, RED, WHITE, YELLOW,
    draw_page,
)

DOC_TYPE   = "iso27001"
VIOLET     = colors.HexColor("#8b5cf6")
VIOLET_DIM = colors.HexColor("#3b1f6e")
VIOLET_BG  = colors.HexColor("#13102a")
VIOLET_MID = colors.HexColor("#5b21b6")

STATUS_COLOR = {"compliant": GREEN, "partial": YELLOW, "non_compliant": RED, "na": GRAY}
STATUS_LABEL = {"compliant": "Conforme", "partial": "Partiel", "non_compliant": "Non conforme", "na": "N/A"}
STATUS_BG    = {
    "compliant":     colors.HexColor("#052e16"),
    "partial":       colors.HexColor("#1c1400"),
    "non_compliant": colors.HexColor("#2d0a0a"),
    "na":            colors.HexColor("#111827"),
}
ROW_A = CARD_BG
ROW_B = colors.HexColor("#162032")

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _st(name, **kw) -> ParagraphStyle:
    d = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2, leading=12)
    d.update(kw)
    return ParagraphStyle(name, **d)


def _score_color(pct: int):
    if pct >= 80: return GREEN
    if pct >= 50: return YELLOW
    return RED


def _cat_score(cat_items: list, items: dict) -> int:
    scorable = [it for it in cat_items if items.get(it["id"], "non_compliant") != "na"]
    if not scorable:
        return 0
    pts = sum(
        2 if items.get(it["id"], "non_compliant") == "compliant"
        else 1 if items.get(it["id"], "non_compliant") == "partial" else 0
        for it in scorable
    )
    return round(pts / (len(scorable) * 2) * 100)


# ─────────────────────────────────────────────────────────────────────────────
# Cover page — drawn entirely on canvas
# Layout (from top of A4 = 297 mm):
#   [0-14 mm]   Accent band + logo
#   [16-46 mm]  Title block
#   [52-120 mm] Score card (gauge left, KPI 2×2 right)
#   [126-235 mm] Domain scores grid (2 columns, 5 rows)
#   [282-297 mm] Footer
# ─────────────────────────────────────────────────────────────────────────────

def _draw_cover(canvas, doc, score, score_label, total,
                compliant, partial, nc, na,
                user_email, date_str,
                domain_scores: list[tuple[str, int]]):
    """Full cover page drawn on the canvas (onFirstPage callback).

    domain_scores: list of (label, pct_0_to_100) for each category.
    """
    W, H = PAGE_W, PAGE_H
    sc = _score_color(score)

    canvas.saveState()

    BAND_H  = 18 * mm
    band_cy = H - BAND_H / 2

    # ── Full-page background (no sidebar — clean) ─────────────────────────────
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Top accent band ───────────────────────────────────────────────────────
    canvas.setFillColor(colors.HexColor("#0f0a28"))
    canvas.rect(0, H - BAND_H, W, BAND_H, fill=1, stroke=0)

    # Left stripe on band only (2 mm)
    canvas.setFillColor(VIOLET)
    canvas.rect(0, H - BAND_H, 2 * mm, BAND_H, fill=1, stroke=0)

    # Bottom border line
    canvas.setStrokeColor(VIOLET_MID)
    canvas.setLineWidth(2.5)
    canvas.line(0, H - BAND_H, W, H - BAND_H)

    # ── Left zone: logo circle + wordmark ─────────────────────────────────────
    logo_cx = MARGIN + 5 * mm   # circle centre x
    logo_r  = 4.2 * mm

    # Outer circle (CYAN)
    canvas.setFillColor(CYAN)
    canvas.circle(logo_cx, band_cy, logo_r, fill=1, stroke=0)
    # Inner circle — slightly lighter to simulate depth
    canvas.setFillColor(colors.HexColor("#22d3ee"))
    canvas.circle(logo_cx - 0.6 * mm, band_cy + 0.6 * mm, logo_r * 0.55, fill=1, stroke=0)
    # "CS" monogram
    canvas.setFillColor(colors.HexColor("#083344"))
    canvas.setFont("Helvetica-Bold", 6.5)
    canvas.drawCentredString(logo_cx, band_cy - 1.1 * mm, "CS")

    # "CyberScan" wordmark
    wm_x = logo_cx + logo_r + 3 * mm
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(wm_x, band_cy - 2 * mm, "CyberScan")

    # ── Centre: thin horizontal rule connecting both zones ────────────────────
    rule_x0 = wm_x + 54   # right edge of wordmark  (approx)
    rule_x1 = W - MARGIN - 42 * mm
    if rule_x1 > rule_x0 + 10:
        canvas.setStrokeColor(colors.HexColor("#2d1b69"))
        canvas.setLineWidth(0.6)
        canvas.line(rule_x0 + 3 * mm, band_cy, rule_x1 - 3 * mm, band_cy)

    # ── Right zone: document type (stacked) ───────────────────────────────────
    # Line 1: "RAPPORT ISO 27001:2022"  bold violet
    canvas.setFillColor(colors.HexColor("#c4b5fd"))
    canvas.setFont("Helvetica-Bold", 8.5)
    canvas.drawRightString(W - MARGIN, band_cy + 1.5 * mm, "RAPPORT ISO 27001:2022")
    # Line 2: date  small gray
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(W - MARGIN, band_cy - 4 * mm, date_str[:10])

    # ── Title block (22–56 mm from top) ──────────────────────────────────────
    # Left accent bar  (3 mm wide × 22 mm tall, aligned with the two title lines)
    acc_x = MARGIN
    acc_y = H - 56 * mm        # bottom of accent bar
    canvas.setFillColor(VIOLET_MID)
    canvas.roundRect(acc_x, acc_y, 3 * mm, 22 * mm, radius=1 * mm, fill=1, stroke=0)

    tx = MARGIN + 7 * mm       # text starts 7 mm right of margin (4 mm right of bar)
    ty = H - 26 * mm           # baseline of main title

    canvas.setFillColor(VIOLET)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(tx, ty, "Rapport de conformite")

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 17)
    canvas.drawString(tx, ty - 9 * mm, "ISO/IEC 27001:2022")

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(tx, ty - 16 * mm, f"Genere le {date_str}  \u2022  {user_email}")

    # ── Score card (52–120 mm from top, i.e. card_y = H-120mm, card_h=68mm) ──
    card_y = H - 120 * mm   # bottom edge of card
    card_h = 68 * mm
    card_w = W - 2 * MARGIN
    left_w  = card_w * 0.40
    right_w = card_w * 0.60

    # "SYNTHÈSE" label above card
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(MARGIN, card_y + card_h + 4 * mm, "SYNTHESE DE CONFORMITE")

    # Card background
    canvas.setFillColor(colors.HexColor("#141e30"))
    canvas.roundRect(MARGIN, card_y, card_w, card_h, radius=4 * mm, fill=1, stroke=0)
    # Violet top stripe on card
    canvas.setFillColor(VIOLET_MID)
    canvas.roundRect(MARGIN, card_y + card_h - 1.5 * mm, card_w, 1.5 * mm,
                     radius=2 * mm, fill=1, stroke=0)

    # ── Gauge (left 40% of card) ──────────────────────────────────────────────
    cx = MARGIN + left_w / 2
    cy = card_y + card_h / 2 + 5 * mm
    r  = 20 * mm

    # Grey track: CCW from 0° to 180° = upper semicircle
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(13)
    canvas.setLineCap(0)   # butt caps — no round blobs
    p = canvas.beginPath()
    p.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)
    canvas.drawPath(p, stroke=1, fill=0)

    # Colored fill: fills from left (180°) toward right (0°) as score grows.
    # fill_extent = score/100 * 180;  start_a = 180 - fill_extent
    # When score=50 → start_a=90, extent=90  → left half filled ✓
    # When score=100 → start_a=0,  extent=180 → full arc ✓
    if score > 0:
        fill_extent = min(score / 100 * 180, 180)
        start_a = 180 - fill_extent
        canvas.setStrokeColor(sc)
        canvas.setLineWidth(13)
        canvas.setLineCap(0)
        p2 = canvas.beginPath()
        p2.arc(cx - r, cy - r, cx + r, cy + r, startAng=start_a, extent=fill_extent)
        canvas.drawPath(p2, stroke=1, fill=0)

    # Mask center (donut effect)
    canvas.setFillColor(colors.HexColor("#141e30"))
    canvas.circle(cx, cy, r - 7 * mm, fill=1, stroke=0)

    # Score % inside gauge
    canvas.setFillColor(sc)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawCentredString(cx, cy - 3.5 * mm, f"{score}%")

    # Grade label below gauge
    canvas.setFillColor(sc)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawCentredString(cx, card_y + 11 * mm, score_label)

    # Controls count
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(cx, card_y + 5.5 * mm, f"{total} controles")

    # Vertical separator between gauge and KPIs
    sep_x = MARGIN + left_w + 4 * mm
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(0.8)
    canvas.line(sep_x, card_y + 8 * mm, sep_x, card_y + card_h - 8 * mm)

    # ── KPI 2×2 grid (right 60% of card) ─────────────────────────────────────
    kpis = [
        (compliant, "Conformes",  GREEN,  colors.HexColor("#052e16")),
        (partial,   "Partiels",   YELLOW, colors.HexColor("#1c1400")),
        (nc,        "Non conf.",  RED,    colors.HexColor("#2d0a0a")),
        (na,        "N/A",        GRAY,   colors.HexColor("#111827")),
    ]
    gx0    = MARGIN + left_w + 8 * mm
    gw     = right_w - 12 * mm
    cell_w = gw / 2 - 2 * mm
    cell_h = card_h / 2 - 5 * mm

    for i, (val, lbl, col, bg) in enumerate(kpis):
        col_i = i % 2
        row_i = i // 2
        kx = gx0 + col_i * (cell_w + 4 * mm)
        ky = card_y + card_h - (row_i + 1) * (cell_h + 4 * mm) + 2 * mm

        canvas.setFillColor(bg)
        canvas.roundRect(kx, ky, cell_w, cell_h, radius=2.5 * mm, fill=1, stroke=0)

        # Top color stripe
        canvas.setFillColor(col)
        canvas.roundRect(kx, ky + cell_h - 1.5 * mm, cell_w, 1.5 * mm,
                         radius=1 * mm, fill=1, stroke=0)

        # Count value
        canvas.setFillColor(col)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(kx + cell_w / 2, ky + cell_h / 2, str(val))

        # Label
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(kx + cell_w / 2, ky + 3.5 * mm, lbl)

    # ── Domain scores grid ────────────────────────────────────────────────────
    # Available vertical space: from 10mm below card to 20mm above footer
    # card_y = bottom of card; footer line at 12mm from bottom
    dom_available = card_y - 8 * mm - 20 * mm   # usable height for grid
    num_dom = len(domain_scores)                  # 10
    ncols   = 2
    nrows   = (num_dom + ncols - 1) // ncols      # 5

    # Section label
    dom_top = card_y - 8 * mm   # top of domain section (just below card)
    canvas.setFillColor(colors.HexColor("#6b7280"))
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(MARGIN, dom_top, "RESULTATS PAR DOMAINE")

    # Row height fills the available space evenly
    gap_h   = 3 * mm
    row_h   = (dom_available - gap_h) / nrows   # height per row incl. gap
    col_gap = 4 * mm
    col_w   = (card_w - col_gap) / ncols        # full column width

    for idx, (lbl, pct) in enumerate(domain_scores):
        col_i  = idx % ncols
        row_i  = idx // ncols
        dx     = MARGIN + col_i * (col_w + col_gap)
        # cell_y = bottom of cell (y increases upward in PDF)
        cell_y = dom_top - (row_i + 1) * row_h - row_i * gap_h + gap_h
        cell_h = row_h - gap_h

        dom_col = _score_color(pct)

        # Cell background
        canvas.setFillColor(colors.HexColor("#0e1623"))
        canvas.roundRect(dx, cell_y, col_w, cell_h, radius=2 * mm, fill=1, stroke=0)

        # Left accent: thick stroke line contained inside the cell's rounded corners.
        # Line center at dx+2mm, width=4mm → spans dx to dx+4mm.
        # Endpoints inset by r_cell so line never exits the rounded area.
        r_cell = 2 * mm
        canvas.setStrokeColor(dom_col)
        canvas.setLineWidth(4 * mm)
        canvas.setLineCap(0)   # butt caps — no extension beyond endpoints
        canvas.line(dx + 2 * mm, cell_y + r_cell,
                    dx + 2 * mm, cell_y + cell_h - r_cell)

        # Domain label (vertically centred upper half)
        inner_x = dx + 7 * mm
        label_y = cell_y + cell_h * 0.55
        canvas.setFillColor(WHITE)
        canvas.setFont("Helvetica-Bold", 7.5)
        short_lbl = lbl if len(lbl) <= 26 else lbl[:25] + "…"
        canvas.drawString(inner_x, label_y, short_lbl)

        # Progress bar (lower half of cell)
        bar_x   = inner_x
        bar_y   = cell_y + cell_h * 0.18
        bar_w   = col_w - inner_x + dx - 12 * mm
        bar_h_v = 3.5 * mm
        canvas.setFillColor(colors.HexColor("#1e293b"))
        canvas.roundRect(bar_x, bar_y, bar_w, bar_h_v, radius=1 * mm, fill=1, stroke=0)
        if pct > 0:
            canvas.setFillColor(dom_col)
            canvas.roundRect(bar_x, bar_y, max(bar_w * pct / 100, 2 * mm), bar_h_v,
                             radius=1 * mm, fill=1, stroke=0)

        # Percentage — right-aligned, vertically centred
        canvas.setFillColor(dom_col)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawRightString(dx + col_w - 3 * mm, cell_y + cell_h * 0.38, f"{pct}%")

    # ── Footer ────────────────────────────────────────────────────────────────
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 12 * mm, W - MARGIN, 12 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 7 * mm, "CyberScan — confidentiel")
    canvas.drawCentredString(W / 2, 7 * mm, "Page 1")
    canvas.drawRightString(W - MARGIN, 7 * mm, date_str[:10])

    canvas.restoreState()


# ─────────────────────────────────────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_iso27001_pdf(
    categories: list[dict],
    items: dict[str, str],
    score: int,
    updated_at: datetime | None,
    user_email: str,
) -> bytes:
    buf = io.BytesIO()
    W   = PAGE_W - 30 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=22 * mm, bottomMargin=18 * mm,
    )

    date_str    = updated_at.strftime("%d/%m/%Y à %H:%M") if updated_at else datetime.utcnow().strftime("%d/%m/%Y à %H:%M")
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"

    all_ids     = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = sum(1 for i in all_ids if items.get(i, "non_compliant") == "compliant")
    partial_n   = sum(1 for i in all_ids if items.get(i, "non_compliant") == "partial")
    nc_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "non_compliant")
    na_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "na")

    # Pre-compute per-domain scores for the cover page
    domain_scores: list[tuple[str, int]] = [
        (cat["label"], _cat_score(cat["items"], items))
        for cat in categories
    ]

    # Cover is page 1 (drawn by onFirstPage). Content starts on page 2.
    story: list = [PageBreak()]

    # ── SUMMARY TABLE ─────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé par domaine",
                            _st("Sec", fontSize=13, fontName="Helvetica-Bold",
                                textColor=VIOLET, spaceBefore=4, spaceAfter=4)))
    story.append(HRFlowable(width=W, thickness=1.2, color=VIOLET, spaceAfter=6))

    hdr   = _st("TH", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)
    col_w = [W * 0.34, W * 0.30, W * 0.09, W * 0.09, W * 0.10, W * 0.08]

    summary_rows = [[
        Paragraph("Domaine", hdr),
        Paragraph("Score",   hdr),
        Paragraph("✓ Conf.", _st("H1", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
        Paragraph("~ Part.", _st("H2", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)),
        Paragraph("✗ N.C.",  _st("H3", fontSize=8, fontName="Helvetica-Bold", textColor=RED)),
        Paragraph("— N/A",   _st("H4", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
    ]]

    for cat in categories:
        cat_items = cat["items"]
        c  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "compliant")
        p  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "partial")
        n  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "non_compliant")
        na = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "na")
        pct       = _cat_score(cat_items, items)
        bar_color = _score_color(pct)
        bar_w     = W * 0.30 - 16
        bar_h     = 8
        filled    = max(bar_w * pct / 100, 0)
        empty     = bar_w - filled

        if pct <= 0:
            bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
        elif pct >= 100:
            bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bar_color),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
        else:
            bar = Table([["", ""]], colWidths=[filled, empty], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), bar_color),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#1e293b")),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))

        summary_rows.append([
            Paragraph(cat["label"], _st(f"CL{cat['id']}", fontSize=8, textColor=WHITE)),
            [bar, Paragraph(f"{pct}%",
                             _st(f"BP{cat['id']}", fontSize=7, fontName="Helvetica-Bold",
                                 textColor=bar_color, spaceBefore=2))],
            Paragraph(str(c),  _st(f"CC{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=GREEN,  alignment=1)),
            Paragraph(str(p),  _st(f"CP{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=YELLOW, alignment=1)),
            Paragraph(str(n),  _st(f"CN{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=RED,    alignment=1)),
            Paragraph(str(na), _st(f"CA{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=GRAY,   alignment=1)),
        ])

    summary_table = Table(summary_rows, colWidths=col_w)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.HexColor("#0c0f1a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_A, ROW_B]),
        ("TOPPADDING",     (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
        ("LEFTPADDING",    (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",           (0, 0), (-1, -1), 0.3, BORDER),
        ("ALIGN",          (2, 0), (-1, -1), "CENTER"),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW",      (0, 0), (-1, 0),  1, VIOLET),
        ("LINEBEFORE",     (0, 1), (0, -1),  3, VIOLET_DIM),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8 * mm))

    # ── DETAIL CHECKLIST ──────────────────────────────────────────────────────
    story.append(Paragraph("Détail des contrôles",
                            _st("Sec2", fontSize=13, fontName="Helvetica-Bold",
                                textColor=VIOLET, spaceBefore=4, spaceAfter=4)))
    story.append(HRFlowable(width=W, thickness=1.2, color=VIOLET, spaceAfter=6))

    for cat in categories:
        pct = _cat_score(cat["items"], items)
        sc  = _score_color(pct)

        # Category header row
        hdr_row = Table([[
            Paragraph(cat["label"],
                      _st(f"CH{cat['id']}", fontSize=10, fontName="Helvetica-Bold",
                          textColor=VIOLET, leading=14)),
            Paragraph(f"{pct}%",
                      _st(f"CS{cat['id']}", fontSize=9, fontName="Helvetica-Bold",
                          textColor=sc, alignment=2)),
        ]], colWidths=[W * 0.85, W * 0.15])
        hdr_row.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), VIOLET_BG),
            ("TOPPADDING",    (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ("LEFTPADDING",   (0, 0), (-1, -1), 12),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("LINEBEFORE",    (0, 0), (0, 0),   4, VIOLET),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.8, VIOLET),
        ]))

        item_rows = []
        item_ts   = []

        for row_idx, it in enumerate(cat["items"]):
            status = items.get(it["id"], "non_compliant")
            sc_col = STATUS_COLOR.get(status, GRAY)
            sl     = STATUS_LABEL.get(status, status)

            badge = Table(
                [[Paragraph(sl, _st(f"Bdg{it['id']}", fontSize=7,
                                    fontName="Helvetica-Bold", textColor=sc_col,
                                    alignment=1))]],
                colWidths=[26 * mm],
            )
            badge.setStyle(TableStyle([
                ("BACKGROUND",    (0, 0), (-1, -1), STATUS_BG.get(status, CARD_BG)),
                ("TOPPADDING",    (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING",   (0, 0), (-1, -1), 3),
                ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
                ("BOX",           (0, 0), (-1, -1), 0.7, sc_col),
                ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ]))

            content = [
                Paragraph(it["label"], _st(f"Lb{it['id']}", fontSize=8,
                                            fontName="Helvetica-Bold", textColor=WHITE, leading=11)),
                Paragraph(it["desc"],  _st(f"Dc{it['id']}", fontSize=7,
                                            textColor=GRAY, leading=10, spaceAfter=0)),
            ]
            item_rows.append([badge, content])
            item_ts.append(("BACKGROUND", (0, row_idx), (0, row_idx),
                             STATUS_BG.get(status, CARD_BG)))

        items_table = Table(item_rows, colWidths=[W * 0.18, W * 0.82])
        ts = [
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [ROW_A, ROW_B]),
            ("TOPPADDING",     (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING",  (0, 0), (-1, -1), 7),
            ("LEFTPADDING",    (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",   (0, 0), (-1, -1), 8),
            ("VALIGN",         (0, 0), (-1, -1), "TOP"),
            ("ALIGN",          (0, 0), (0, -1),  "CENTER"),
            ("VALIGN",         (0, 0), (0, -1),  "MIDDLE"),
            ("GRID",           (0, 0), (-1, -1), 0.3, BORDER),
        ] + item_ts
        items_table.setStyle(TableStyle(ts))
        story.append(KeepTogether([hdr_row, items_table]))
        story.append(Spacer(1, 4 * mm))

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Rapport ISO 27001:2022 généré par CyberScan le "
        f"{datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas une certification ISO/IEC 27001.",
        _st("Disc", fontSize=7, textColor=GRAY),
    ))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    def _first_page(canvas, doc):
        _draw_cover(
            canvas, doc,
            score=score, score_label=score_label, total=total_items,
            compliant=compliant_n, partial=partial_n, nc=nc_n, na=na_n,
            user_email=user_email, date_str=date_str,
            domain_scores=domain_scores,
        )

    def _later_pages(canvas, doc):
        draw_page(canvas, doc, DOC_TYPE, "Conformité ISO 27001:2022", "")

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
    return buf.getvalue()
