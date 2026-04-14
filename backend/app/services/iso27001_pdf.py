"""
ISO 27001:2022 Compliance PDF — redesigned visual.
"""
from __future__ import annotations

import io
import math
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
    draw_page, section_rule,
)

DOC_TYPE = "iso27001"
VIOLET   = colors.HexColor("#8b5cf6")
VIOLET_BG = colors.HexColor("#1e1333")
VIOLET_DIM = colors.HexColor("#4c1d95")

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


def _score_bg(pct: int):
    if pct >= 80: return colors.HexColor("#052e16")
    if pct >= 50: return colors.HexColor("#1c1400")
    return colors.HexColor("#2d0a0a")


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
# Score Gauge Flowable
# ─────────────────────────────────────────────────────────────────────────────

class ScoreGauge(Flowable):
    """Semicircle gauge drawn with ReportLab Graphics."""

    def __init__(self, score: int, width=120, height=75):
        super().__init__()
        self.score = score
        self.width = width
        self.height = height

    def draw(self):
        score  = self.score
        cx, cy = self.width / 2, 20
        r_out  = min(self.width, self.height * 1.5) / 2 - 4
        r_in   = r_out - 14
        color  = _score_color(score)

        # Track (grey arc — 180°)
        c = self.canv
        c.saveState()

        # Grey track
        c.setStrokeColor(colors.HexColor("#1e293b"))
        c.setLineWidth(14)
        c.setLineCap(1)
        c.arc(cx - r_out + 7, cy - r_out + 7, cx + r_out - 7, cy + r_out - 7,
              startAng=0, extent=180)

        # Colored fill
        if score > 0:
            c.setStrokeColor(color)
            c.setLineWidth(14)
            c.setLineCap(1)
            c.arc(cx - r_out + 7, cy - r_out + 7, cx + r_out - 7, cy + r_out - 7,
                  startAng=0, extent=min(score / 100 * 180, 180))

        # Score text
        c.setFillColor(color)
        c.setFont("Helvetica-Bold", 26)
        c.drawCentredString(cx, cy + r_out * 0.35, f"{score}%")

        c.restoreState()

    def wrap(self, *args):
        return self.width, self.height


# ─────────────────────────────────────────────────────────────────────────────
# Status Badge cell (colored pill background)
# ─────────────────────────────────────────────────────────────────────────────

def _badge_table(status: str) -> Table:
    label = STATUS_LABEL.get(status, status)
    color = STATUS_COLOR.get(status, GRAY)
    bg    = STATUS_BG.get(status, CARD_BG)
    t = Table([[Paragraph(label, _st(f"Bdg_{status}_{id(status)}", fontSize=7,
                                     fontName="Helvetica-Bold", textColor=color,
                                     alignment=1))]], colWidths=[28*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), bg),
        ("ROUNDEDCORNERS",[3]),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING",   (0,0), (-1,-1), 4),
        ("RIGHTPADDING",  (0,0), (-1,-1), 4),
        ("BOX",           (0,0), (-1,-1), 0.5, color),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    return t


# ─────────────────────────────────────────────────────────────────────────────
# Cover page flowable
# ─────────────────────────────────────────────────────────────────────────────

class CoverPage(Flowable):
    def __init__(self, score: int, score_label: str, total: int,
                 compliant: int, partial: int, nc: int, na: int,
                 user_email: str, date_str: str, page_w: float, page_h: float):
        super().__init__()
        self.score       = score
        self.score_label = score_label
        self.total       = total
        self.compliant   = compliant
        self.partial     = partial
        self.nc          = nc
        self.na          = na
        self.user_email  = user_email
        self.date_str    = date_str
        self.width       = page_w - 30 * mm
        self.height      = page_h - 50 * mm

    def draw(self):
        c   = self.canv
        W   = self.width
        sc  = _score_color(self.score)
        sc_bg = _score_bg(self.score)

        c.saveState()

        # ── Title block ──────────────────────────────────────────────────────
        c.setFillColor(VIOLET)
        c.setFont("Helvetica-Bold", 28)
        c.drawString(0, self.height - 10*mm, "Rapport de conformité")
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 22)
        c.drawString(0, self.height - 22*mm, "ISO/IEC 27001:2022")

        # Accent line under title
        c.setStrokeColor(VIOLET)
        c.setLineWidth(2)
        c.line(0, self.height - 26*mm, 80*mm, self.height - 26*mm)

        # Meta
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 9)
        c.drawString(0, self.height - 33*mm, f"Généré le {self.date_str}  ·  {self.user_email}")

        # ── Score hero card ───────────────────────────────────────────────────
        card_y  = self.height - 95*mm
        card_h  = 55*mm
        card_w  = W

        # Card background
        c.setFillColor(CARD_BG)
        c.roundRect(0, card_y, card_w, card_h, radius=4*mm, fill=1, stroke=0)

        # Left score block
        left_w = 55*mm
        c.setFillColor(sc_bg)
        c.roundRect(0, card_y, left_w, card_h, radius=4*mm, fill=1, stroke=0)
        # clip right side of left block to not round
        c.setFillColor(sc_bg)
        c.rect(left_w - 4*mm, card_y, 4*mm, card_h, fill=1, stroke=0)

        # Score %
        c.setFillColor(sc)
        c.setFont("Helvetica-Bold", 38)
        c.drawCentredString(left_w / 2, card_y + card_h / 2 - 6*mm, f"{self.score}%")
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(left_w / 2, card_y + card_h / 2 + 10*mm, self.score_label)

        # Separator
        c.setStrokeColor(BORDER)
        c.setLineWidth(0.5)
        c.line(left_w + 1*mm, card_y + 5*mm, left_w + 1*mm, card_y + card_h - 5*mm)

        # KPI blocks
        kpis = [
            (self.compliant, "Conformes",    GREEN),
            (self.partial,   "Partiels",     YELLOW),
            (self.nc,        "Non conformes",RED),
            (self.na,        "N/A",          GRAY),
        ]
        kpi_x_start = left_w + 8*mm
        kpi_w       = (card_w - left_w - 10*mm) / 4
        for i, (val, lbl, col) in enumerate(kpis):
            kx = kpi_x_start + i * kpi_w + kpi_w / 2
            ky = card_y + card_h / 2

            # Background tint
            c.setFillColor(STATUS_BG.get(
                ["compliant","partial","non_compliant","na"][i], CARD_BG))
            c.roundRect(kpi_x_start + i*kpi_w, card_y + 6*mm,
                        kpi_w - 3*mm, card_h - 12*mm, radius=2*mm, fill=1, stroke=0)

            c.setFillColor(col)
            c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(kx, ky - 1*mm, str(val))
            c.setFont("Helvetica", 7)
            c.setFillColor(GRAY)
            c.drawCentredString(kx, ky - 8*mm, lbl)

        # Total
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 8)
        c.drawString(left_w + 8*mm, card_y + 2*mm,
                     f"{self.total} contrôles évalués au total")

        c.restoreState()

    def wrap(self, *args):
        return self.width, self.height


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
    PAGE_W, PAGE_H = A4
    W = PAGE_W - 30 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=22*mm, bottomMargin=18*mm,
    )

    story = []
    date_str    = updated_at.strftime("%d/%m/%Y à %H:%M") if updated_at else datetime.utcnow().strftime("%d/%m/%Y à %H:%M")
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"

    all_ids     = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = sum(1 for i in all_ids if items.get(i, "non_compliant") == "compliant")
    partial_n   = sum(1 for i in all_ids if items.get(i, "non_compliant") == "partial")
    nc_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "non_compliant")
    na_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "na")

    # ── COVER ─────────────────────────────────────────────────────────────────
    story.append(CoverPage(
        score=score, score_label=score_label,
        total=total_items,
        compliant=compliant_n, partial=partial_n, nc=nc_n, na=na_n,
        user_email=user_email, date_str=date_str,
        page_w=PAGE_W, page_h=PAGE_H,
    ))
    story.append(Spacer(1, 8*mm))

    # ── DOMAIN SUMMARY TABLE ──────────────────────────────────────────────────
    story.append(Paragraph("Résumé par domaine",
                            _st("Sec", fontSize=13, fontName="Helvetica-Bold",
                                textColor=VIOLET, spaceBefore=6, spaceAfter=4)))
    story.append(HRFlowable(width=W, thickness=1.2, color=VIOLET, spaceAfter=6))

    # Header row
    hdr = _st("TH", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)
    col_w = [W*0.34, W*0.30, W*0.09, W*0.09, W*0.10, W*0.08]

    summary_rows = [[
        Paragraph("Domaine",   hdr),
        Paragraph("Score",     hdr),
        Paragraph("✓",         _st("H1", fontSize=9, fontName="Helvetica-Bold", textColor=GREEN)),
        Paragraph("~",         _st("H2", fontSize=9, fontName="Helvetica-Bold", textColor=YELLOW)),
        Paragraph("✗",         _st("H3", fontSize=9, fontName="Helvetica-Bold", textColor=RED)),
        Paragraph("—",         _st("H4", fontSize=9, fontName="Helvetica-Bold", textColor=GRAY)),
    ]]

    for cat in categories:
        cat_items = cat["items"]
        c  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "compliant")
        p  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "partial")
        n  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "non_compliant")
        na = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "na")
        pct       = _cat_score(cat_items, items)
        bar_color = _score_color(pct)

        bar_w  = W * 0.30 - 16
        bar_h  = 7
        filled = max(bar_w * pct / 100, 0)
        empty  = bar_w - filled

        if pct <= 0:
            bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0,0),(-1,-1), colors.HexColor("#1e293b")),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
            ]))
        elif pct >= 100:
            bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0,0),(-1,-1), bar_color),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
            ]))
        else:
            bar = Table([["", ""]], colWidths=[filled, empty], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND",(0,0),(0,0), bar_color),
                ("BACKGROUND",(1,0),(1,0), colors.HexColor("#1e293b")),
                ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),0),
                ("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
            ]))

        bar_cell = [
            bar,
            Paragraph(f"{pct}%", _st(f"BP{cat['id']}", fontSize=7, fontName="Helvetica-Bold",
                                      textColor=bar_color, spaceBefore=2)),
        ]

        summary_rows.append([
            Paragraph(cat["label"], _st(f"CL{cat['id']}", fontSize=8, textColor=WHITE)),
            bar_cell,
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
        # Violet left accent on each category cell
        ("LINEBEFORE",     (0,1), (0,-1),  3, VIOLET_DIM),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8*mm))

    # ── DETAILED CHECKLIST ────────────────────────────────────────────────────
    story.append(Paragraph("Détail des contrôles",
                            _st("Sec2", fontSize=13, fontName="Helvetica-Bold",
                                textColor=VIOLET, spaceBefore=6, spaceAfter=4)))
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
        ]], colWidths=[W*0.85, W*0.15])
        hdr_row.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#0f0e1f")),
            ("TOPPADDING",    (0,0), (-1,-1), 9),
            ("BOTTOMPADDING", (0,0), (-1,-1), 9),
            ("LEFTPADDING",   (0,0), (-1,-1), 10),
            ("RIGHTPADDING",  (0,0), (-1,-1), 10),
            ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN",         (1,0), (1,0),   "RIGHT"),
            ("LINEBEFORE",    (0,0), (0,0),   4, VIOLET),
            ("LINEBELOW",     (0,0), (-1,-1), 0.8, VIOLET),
        ]))

        # Item rows
        item_rows = []
        item_ts   = []

        for row_idx, it in enumerate(cat["items"]):
            status  = items.get(it["id"], "non_compliant")
            sc_col  = STATUS_COLOR.get(status, GRAY)
            sl      = STATUS_LABEL.get(status, status)

            # Badge cell (colored pill)
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
                ("LEFTPADDING",   (0,0),(-1,-1), 4),
                ("RIGHTPADDING",  (0,0),(-1,-1), 4),
                ("BOX",           (0,0),(-1,-1), 0.6, sc_col),
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
        f"Rapport ISO 27001:2022 généré par CyberScan le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas une certification ISO/IEC 27001.",
        _st("Disc", fontSize=7, textColor=GRAY),
    ))

    doc.build(
        story,
        onFirstPage=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité ISO 27001:2022", user_email),
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité ISO 27001:2022"),
    )
    return buf.getvalue()
