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
from reportlab.platypus.flowables import Flowable

from app.services.pdf_brand import (
    BORDER, CARD_BG, CYAN, DARK_BG, GRAY, GREEN, RED, WHITE, YELLOW,
    draw_page,
)

DOC_TYPE  = "iso27001"
VIOLET    = colors.HexColor("#8b5cf6")
VIOLET_DIM = colors.HexColor("#3b1f6e")
VIOLET_BG  = colors.HexColor("#13102a")

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
# ─────────────────────────────────────────────────────────────────────────────

def _draw_cover(canvas, doc, score, score_label, total,
                compliant, partial, nc, na, user_email, date_str):
    """Full cover page drawn on the canvas (onFirstPage callback)."""
    W, H = PAGE_W, PAGE_H
    sc = _score_color(score)

    canvas.saveState()

    # ── Background ────────────────────────────────────────────────────────────
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # ── Top accent band ───────────────────────────────────────────────────────
    canvas.setFillColor(VIOLET_BG)
    canvas.rect(0, H - 14*mm, W, 14*mm, fill=1, stroke=0)
    canvas.setStrokeColor(VIOLET)
    canvas.setLineWidth(2.5)
    canvas.line(0, H - 1, W, H - 1)

    # Logo box
    lx, ly = MARGIN, H - 10.5*mm
    canvas.setFillColor(CYAN)
    canvas.roundRect(lx, ly, 7*mm, 7*mm, radius=1.5*mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 6)
    canvas.drawCentredString(lx + 3.5*mm, ly + 2*mm, "CS")

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 10)
    canvas.drawString(lx + 9*mm, ly + 1.8*mm, "CyberScan")
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(lx + 9*mm + 42, ly + 1.8*mm, "|")
    canvas.setFillColor(VIOLET)
    canvas.drawString(lx + 9*mm + 50, ly + 1.8*mm, "Conformité ISO 27001:2022")

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(W - MARGIN, ly + 1.8*mm, date_str[:10])

    # ── Left violet side-bar ──────────────────────────────────────────────────
    canvas.setFillColor(VIOLET_BG)
    canvas.rect(0, 0, 8*mm, H - 14*mm, fill=1, stroke=0)
    canvas.setFillColor(VIOLET)
    canvas.rect(0, 0, 2*mm, H - 14*mm, fill=1, stroke=0)

    # ── Title block ───────────────────────────────────────────────────────────
    tx = 16*mm
    ty = H - 40*mm

    canvas.setFillColor(VIOLET)
    canvas.setFont("Helvetica-Bold", 30)
    canvas.drawString(tx, ty, "Rapport de conformité")

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 22)
    canvas.drawString(tx, ty - 14*mm, "ISO/IEC 27001:2022")

    # Underline
    canvas.setStrokeColor(VIOLET)
    canvas.setLineWidth(2)
    canvas.line(tx, ty - 17*mm, tx + 70*mm, ty - 17*mm)

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 9)
    canvas.drawString(tx, ty - 22*mm, f"Généré le {date_str}  ·  {user_email}")

    # ── Score gauge (semicircle) ───────────────────────────────────────────────
    cx = W / 2
    cy = H - 115*mm
    r  = 32*mm

    # Track arc (grey, 180°)
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(18)
    canvas.setLineCap(1)
    p = canvas.beginPath()
    p.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=180)
    canvas.drawPath(p, stroke=1, fill=0)

    # Colored arc (score %)
    if score > 0:
        canvas.setStrokeColor(sc)
        canvas.setLineWidth(18)
        canvas.setLineCap(1)
        p2 = canvas.beginPath()
        p2.arc(cx - r, cy - r, cx + r, cy + r, startAng=0, extent=min(score / 100 * 180, 180))
        canvas.drawPath(p2, stroke=1, fill=0)

    # Center dot
    canvas.setFillColor(DARK_BG)
    canvas.circle(cx, cy, 14*mm, fill=1, stroke=0)

    # Score text
    canvas.setFillColor(sc)
    canvas.setFont("Helvetica-Bold", 36)
    canvas.drawCentredString(cx, cy - 5*mm, f"{score}%")

    # Label below gauge
    canvas.setFillColor(sc)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawCentredString(cx, cy - 40*mm, score_label)

    # Total controls
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 8)
    canvas.drawCentredString(cx, cy - 46*mm, f"{total} contrôles évalués")

    # ── KPI row ───────────────────────────────────────────────────────────────
    kpis = [
        (compliant, "Conformes",     GREEN,  colors.HexColor("#052e16")),
        (partial,   "Partiels",      YELLOW, colors.HexColor("#1c1400")),
        (nc,        "Non conformes", RED,    colors.HexColor("#2d0a0a")),
        (na,        "N/A",           GRAY,   colors.HexColor("#111827")),
    ]

    kpi_y    = H - 175*mm
    kpi_h    = 28*mm
    kpi_total_w = W - 2*MARGIN
    kpi_w    = (kpi_total_w - 3*3*mm) / 4  # 3 gaps of 3mm

    for i, (val, lbl, col, bg) in enumerate(kpis):
        kx = MARGIN + i * (kpi_w + 3*mm)

        # Card background
        canvas.setFillColor(bg)
        canvas.roundRect(kx, kpi_y, kpi_w, kpi_h, radius=3*mm, fill=1, stroke=0)

        # Colored top border
        canvas.setFillColor(col)
        canvas.roundRect(kx, kpi_y + kpi_h - 1.5*mm, kpi_w, 1.5*mm, radius=1*mm, fill=1, stroke=0)

        # Value
        canvas.setFillColor(col)
        canvas.setFont("Helvetica-Bold", 26)
        canvas.drawCentredString(kx + kpi_w/2, kpi_y + kpi_h/2 - 1*mm, str(val))

        # Label
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(kx + kpi_w/2, kpi_y + 4*mm, lbl)

    # ── Footer ────────────────────────────────────────────────────────────────
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 12*mm, W - MARGIN, 12*mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(MARGIN, 7*mm, "CyberScan — confidentiel")
    canvas.drawCentredString(W/2, 7*mm, "Page 1")
    canvas.drawRightString(W - MARGIN, 7*mm, date_str[:10])

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
    W   = PAGE_W - 30*mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=22*mm, bottomMargin=18*mm,
    )

    date_str    = updated_at.strftime("%d/%m/%Y à %H:%M") if updated_at else datetime.utcnow().strftime("%d/%m/%Y à %H:%M")
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"

    all_ids     = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = sum(1 for i in all_ids if items.get(i, "non_compliant") == "compliant")
    partial_n   = sum(1 for i in all_ids if items.get(i, "non_compliant") == "partial")
    nc_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "non_compliant")
    na_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "na")

    # Cover is page 1 (drawn by onFirstPage). Content starts on page 2.
    story: list = [PageBreak()]

    # ── SUMMARY TABLE ─────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé par domaine",
                            _st("Sec", fontSize=13, fontName="Helvetica-Bold",
                                textColor=VIOLET, spaceBefore=4, spaceAfter=4)))
    story.append(HRFlowable(width=W, thickness=1.2, color=VIOLET, spaceAfter=6))

    hdr   = _st("TH", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)
    col_w = [W*0.34, W*0.30, W*0.09, W*0.09, W*0.10, W*0.08]

    summary_rows = [[
        Paragraph("Domaine", hdr),
        Paragraph("Score",   hdr),
        Paragraph("✓ Conf.", _st("H1", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
        Paragraph("~ Part.", _st("H2", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)),
        Paragraph("✗ N.C.", _st("H3", fontSize=8, fontName="Helvetica-Bold", textColor=RED)),
        Paragraph("— N/A",  _st("H4", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
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
            bar.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#1e293b")),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
        elif pct >= 100:
            bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),bar_color),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))
        else:
            bar = Table([["",""]], colWidths=[filled, empty], rowHeights=[bar_h])
            bar.setStyle(TableStyle([("BACKGROUND",(0,0),(0,0),bar_color),
                ("BACKGROUND",(1,0),(1,0),colors.HexColor("#1e293b")),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0)]))

        summary_rows.append([
            Paragraph(cat["label"], _st(f"CL{cat['id']}", fontSize=8, textColor=WHITE)),
            [bar, Paragraph(f"{pct}%", _st(f"BP{cat['id']}", fontSize=7, fontName="Helvetica-Bold",
                                            textColor=bar_color, spaceBefore=2))],
            Paragraph(str(c),  _st(f"CC{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=GREEN,  alignment=1)),
            Paragraph(str(p),  _st(f"CP{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=YELLOW, alignment=1)),
            Paragraph(str(n),  _st(f"CN{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=RED,    alignment=1)),
            Paragraph(str(na), _st(f"CA{cat['id']}", fontSize=9, fontName="Helvetica-Bold", textColor=GRAY,   alignment=1)),
        ])

    summary_table = Table(summary_rows, colWidths=col_w)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",     (0,0), (-1,0),  colors.HexColor("#0c0f1a")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [ROW_A, ROW_B]),
        ("TOPPADDING",     (0,0), (-1,-1), 7),
        ("BOTTOMPADDING",  (0,0), (-1,-1), 7),
        ("LEFTPADDING",    (0,0), (-1,-1), 8),
        ("RIGHTPADDING",   (0,0), (-1,-1), 8),
        ("GRID",           (0,0), (-1,-1), 0.3, BORDER),
        ("ALIGN",          (2,0), (-1,-1), "CENTER"),
        ("VALIGN",         (0,0), (-1,-1), "MIDDLE"),
        ("LINEBELOW",      (0,0), (-1,0),  1, VIOLET),
        ("LINEBEFORE",     (0,1), (0,-1),  3, VIOLET_DIM),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8*mm))

    # ── DETAIL CHECKLIST ──────────────────────────────────────────────────────
    story.append(Paragraph("Détail des contrôles",
                            _st("Sec2", fontSize=13, fontName="Helvetica-Bold",
                                textColor=VIOLET, spaceBefore=4, spaceAfter=4)))
    story.append(HRFlowable(width=W, thickness=1.2, color=VIOLET, spaceAfter=6))

    for cat in categories:
        pct = _cat_score(cat["items"], items)
        sc  = _score_color(pct)

        # Category header
        hdr_row = Table([[
            Paragraph(cat["label"],
                      _st(f"CH{cat['id']}", fontSize=10, fontName="Helvetica-Bold",
                          textColor=VIOLET, leading=14)),
            Paragraph(f"{pct}%",
                      _st(f"CS{cat['id']}", fontSize=9, fontName="Helvetica-Bold",
                          textColor=sc, alignment=2)),
        ]], colWidths=[W*0.85, W*0.15])
        hdr_row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), VIOLET_BG),
            ("TOPPADDING",    (0,0), (-1,-1), 9),
            ("BOTTOMPADDING", (0,0), (-1,-1), 9),
            ("LEFTPADDING",   (0,0), (-1,-1), 12),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN",         (1,0), (1,0),   "RIGHT"),
            ("LINEBEFORE",    (0,0), (0,0),   4, VIOLET),
            ("LINEBELOW",     (0,0), (-1,-1), 0.8, VIOLET),
        ]))

        item_rows = []
        item_ts   = []

        for row_idx, it in enumerate(cat["items"]):
            status = items.get(it["id"], "non_compliant")
            sc_col = STATUS_COLOR.get(status, GRAY)
            sl     = STATUS_LABEL.get(status, status)

            # Pill badge
            badge = Table(
                [[Paragraph(sl, _st(f"Bdg{it['id']}", fontSize=7,
                                    fontName="Helvetica-Bold", textColor=sc_col,
                                    alignment=1))]],
                colWidths=[26*mm],
            )
            badge.setStyle(TableStyle([
                ("BACKGROUND",    (0,0),(-1,-1), STATUS_BG.get(status, CARD_BG)),
                ("TOPPADDING",    (0,0),(-1,-1), 4),
                ("BOTTOMPADDING", (0,0),(-1,-1), 4),
                ("LEFTPADDING",   (0,0),(-1,-1), 3),
                ("RIGHTPADDING",  (0,0),(-1,-1), 3),
                ("BOX",           (0,0),(-1,-1), 0.7, sc_col),
                ("ALIGN",         (0,0),(-1,-1), "CENTER"),
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

        items_table = Table(item_rows, colWidths=[W*0.18, W*0.82])
        ts = [
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [ROW_A, ROW_B]),
            ("TOPPADDING",     (0,0), (-1,-1), 7),
            ("BOTTOMPADDING",  (0,0), (-1,-1), 7),
            ("LEFTPADDING",    (0,0), (-1,-1), 8),
            ("RIGHTPADDING",   (0,0), (-1,-1), 8),
            ("VALIGN",         (0,0), (-1,-1), "TOP"),
            ("ALIGN",          (0,0), (0,-1),  "CENTER"),
            ("VALIGN",         (0,0), (0,-1),  "MIDDLE"),
            ("GRID",           (0,0), (-1,-1), 0.3, BORDER),
        ] + item_ts
        items_table.setStyle(TableStyle(ts))
        story.append(KeepTogether([hdr_row, items_table]))
        story.append(Spacer(1, 4*mm))

    # ── DISCLAIMER ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Rapport ISO 27001:2022 généré par CyberScan le "
        f"{datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas une certification ISO/IEC 27001.",
        _st("Disc", fontSize=7, textColor=GRAY),
    ))

    # ── BUILD ─────────────────────────────────────────────────────────────────
    def _first_page(canvas, doc):
        _draw_cover(canvas, doc,
                    score=score, score_label=score_label, total=total_items,
                    compliant=compliant_n, partial=partial_n, nc=nc_n, na=na_n,
                    user_email=user_email, date_str=date_str)

    def _later_pages(canvas, doc):
        draw_page(canvas, doc, DOC_TYPE, "Conformité ISO 27001:2022", "")

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
    return buf.getvalue()
