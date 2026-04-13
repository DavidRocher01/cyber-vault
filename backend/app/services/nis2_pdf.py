"""
NIS2 Compliance PDF report generator using ReportLab.
Uses shared visual identity from pdf_brand.
"""

from __future__ import annotations

import io
from datetime import datetime

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
    KeepTogether,
)

from app.services.pdf_brand import (
    BORDER,
    CARD_BG,
    CYAN,
    DARK_BG,
    GRAY,
    GREEN,
    ORANGE,
    RED,
    WHITE,
    YELLOW,
    draw_page,
    get_styles,
    section_rule,
)

DOC_TYPE = "nis2"

STATUS_COLOR = {
    "compliant":     GREEN,
    "partial":       YELLOW,
    "non_compliant": RED,
    "na":            GRAY,
}
STATUS_LABEL = {
    "compliant":     "Conforme",
    "partial":       "Partiel",
    "non_compliant": "Non conforme",
    "na":            "N/A",
}
STATUS_BG = {
    "compliant":     colors.HexColor("#14532d"),
    "partial":       colors.HexColor("#713f12"),
    "non_compliant": colors.HexColor("#7f1d1d"),
    "na":            colors.HexColor("#1e293b"),
}

PURPLE = colors.HexColor("#8b5cf6")


def _style(name, **kwargs) -> ParagraphStyle:
    defaults = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2)
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


def _progress_bar(pct: int, width: float, height: float = 5, color=CYAN) -> Table:
    """Return a thin horizontal progress bar as a 1×1 Table."""
    filled = max(width * pct / 100, 0)
    empty  = width - filled
    if filled <= 0:
        data = [[""]]
        t = Table(data, colWidths=[width], rowHeights=[height])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        return t
    data = [["", ""]]
    t = Table(data, colWidths=[filled, empty], rowHeights=[height])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), color),
        ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#1e293b")),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    return t


def _score_color(pct: int):
    if pct >= 80: return GREEN
    if pct >= 50: return YELLOW
    return RED


def _score_bg(pct: int):
    if pct >= 80: return colors.HexColor("#14532d")
    if pct >= 50: return colors.HexColor("#713f12")
    return colors.HexColor("#7f1d1d")


def generate_nis2_pdf(
    categories: list[dict],
    items: dict[str, str],
    score: int,
    updated_at: datetime | None,
    user_email: str,
) -> bytes:
    buf = io.BytesIO()
    W = A4[0] - 30 * mm

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=25 * mm, bottomMargin=20 * mm,
    )

    st = get_styles(DOC_TYPE)
    section_st = st["section"]

    date_str    = updated_at.strftime("%d/%m/%Y") if updated_at else datetime.utcnow().strftime("%d/%m/%Y")
    sc          = _score_color(score)
    sc_bg       = _score_bg(score)
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"

    # Counts
    all_ids     = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = sum(1 for i in all_ids if items.get(i, "non_compliant") == "compliant")
    partial_n   = sum(1 for i in all_ids if items.get(i, "non_compliant") == "partial")
    nc_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "non_compliant")
    na_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "na")

    story = []

    # ── SCORE HERO ──────────────────────────────────────────────────────────────
    # Left: big score + level badge
    score_num_st  = _style("ScN", fontSize=48, fontName="Helvetica-Bold", textColor=sc, leading=52)
    level_badge_st = _style("LvB", fontSize=11, fontName="Helvetica-Bold", textColor=sc)
    date_small_st  = _style("DS",  fontSize=7,  textColor=GRAY)

    left_cell = [
        Paragraph(f"{score}%", score_num_st),
        Spacer(1, 2),
        Paragraph(score_label, level_badge_st),
        Spacer(1, 4),
        Paragraph(f"Dernière mise à jour : {date_str}", date_small_st),
    ]

    # Right: 4 KPI tiles
    kpi_w = (W * 0.65 - 8) / 4

    def kpi_table(value: int, label: str, color, bg) -> Table:
        val_st = _style(f"KV{label}", fontSize=22, fontName="Helvetica-Bold", textColor=color, leading=26)
        lbl_st = _style(f"KL{label}", fontSize=7,  textColor=GRAY)
        t = Table([[Paragraph(str(value), val_st)], [Paragraph(label, lbl_st)]],
                  colWidths=[kpi_w])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), bg),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ROUNDEDCORNERS", [5]),
        ]))
        return t

    kpi_row = Table([[
        kpi_table(compliant_n, "Conformes",      GREEN,  colors.HexColor("#052e16")),
        kpi_table(partial_n,   "Partiels",        YELLOW, colors.HexColor("#1c1400")),
        kpi_table(nc_n,        "Non conformes",   RED,    colors.HexColor("#2d0a0a")),
        kpi_table(na_n,        "N/A",             GRAY,   colors.HexColor("#0f172a")),
    ]], colWidths=[kpi_w] * 4, hAlign="CENTER")
    kpi_row.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    total_st  = _style("Tot", fontSize=8, textColor=GRAY)
    right_cell = [kpi_row, Spacer(1, 6), Paragraph(f"{total_items} critères évalués au total", total_st)]

    hero = Table(
        [[left_cell, right_cell]],
        colWidths=[W * 0.35, W * 0.65],
    )
    hero.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
        ("BACKGROUND",    (0, 0), (0, 0),   sc_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 16),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 16),
        ("LEFTPADDING",   (0, 0), (-1, -1), 18),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 18),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",     (0, 0), (0, -1),  0.5, BORDER),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(hero)
    story.append(Spacer(1, 7 * mm))

    # ── CATEGORY SUMMARY ────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé par catégorie", section_st))
    story.append(section_rule(W, DOC_TYPE))

    # Header row
    hdr_st = _style("TH", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)
    cat_rows = [[
        Paragraph("Catégorie", hdr_st),
        Paragraph("Score", hdr_st),
        Paragraph("Progression", hdr_st),
        Paragraph("✓", _style("TH1", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
        Paragraph("~", _style("TH2", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)),
        Paragraph("✗", _style("TH3", fontSize=8, fontName="Helvetica-Bold", textColor=RED)),
        Paragraph("—", _style("TH4", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
    ]]

    bar_col_w = W * 0.26
    col_widths = [W * 0.30, W * 0.08, bar_col_w, W * 0.09, W * 0.09, W * 0.10, W * 0.08]

    for cat in categories:
        cat_items = cat["items"]
        c  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "compliant")
        p  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "partial")
        n  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "non_compliant")
        na = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "na")

        scorable = [it for it in cat_items if items.get(it["id"], "non_compliant") != "na"]
        if scorable:
            pts    = sum(2 if items.get(it["id"], "non_compliant") == "compliant"
                         else 1 if items.get(it["id"], "non_compliant") == "partial" else 0
                         for it in scorable)
            cat_pct = round(pts / (len(scorable) * 2) * 100)
        else:
            cat_pct = 0

        bar_color = _score_color(cat_pct)
        bar = _progress_bar(cat_pct, bar_col_w - 6, height=6, color=bar_color)

        pct_st = _style(f"CS{cat['id']}", fontSize=8, fontName="Helvetica-Bold",
                        textColor=_score_color(cat_pct))

        cat_rows.append([
            Paragraph(cat["label"], _style(f"CL{cat['id']}", fontSize=8, textColor=WHITE)),
            Paragraph(f"{cat_pct}%", pct_st),
            bar,
            Paragraph(str(c),  _style(f"CC{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
            Paragraph(str(p),  _style(f"CP{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)),
            Paragraph(str(n),  _style(f"CN{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=RED)),
            Paragraph(str(na), _style(f"CA{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
        ])

    cat_table = Table(cat_rows, colWidths=col_widths)
    ts = [
        ("BACKGROUND",    (0, 0), (-1, 0),   colors.HexColor("#0f172a")),
        ("BACKGROUND",    (0, 1), (-1, -1),  CARD_BG),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1),  [CARD_BG, colors.HexColor("#162032")]),
        ("FONTNAME",      (0, 0), (-1, 0),   "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1),  8),
        ("TOPPADDING",    (0, 0), (-1, -1),  6),
        ("BOTTOMPADDING", (0, 0), (-1, -1),  6),
        ("LEFTPADDING",   (0, 0), (-1, -1),  8),
        ("RIGHTPADDING",  (0, 0), (-1, -1),  6),
        ("GRID",          (0, 0), (-1, -1),  0.3, BORDER),
        ("ALIGN",         (1, 0), (-1, -1),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1),  "MIDDLE"),
        ("LINEBELOW",     (0, 0), (-1, 0),   1, BORDER),
    ]
    cat_table.setStyle(TableStyle(ts))
    story.append(cat_table)
    story.append(Spacer(1, 7 * mm))

    # ── DETAILED CHECKLIST ───────────────────────────────────────────────────────
    story.append(Paragraph("Détail des critères", section_st))
    story.append(section_rule(W, DOC_TYPE))

    for cat in categories:
        # Compute category score for header badge
        scorable = [it for it in cat["items"] if items.get(it["id"], "non_compliant") != "na"]
        if scorable:
            pts = sum(2 if items.get(it["id"], "non_compliant") == "compliant"
                      else 1 if items.get(it["id"], "non_compliant") == "partial" else 0
                      for it in scorable)
            cat_pct = round(pts / (len(scorable) * 2) * 100)
        else:
            cat_pct = 0

        # Category header row (spans full width)
        cat_hdr_st   = _style(f"CH{cat['id']}", fontSize=9, fontName="Helvetica-Bold",
                               textColor=CYAN, leading=13)
        cat_score_st = _style(f"CS2{cat['id']}", fontSize=8, fontName="Helvetica-Bold",
                               textColor=_score_color(cat_pct))

        hdr_row = Table([[
            Paragraph(cat["label"], cat_hdr_st),
            Paragraph(f"{cat_pct}%", cat_score_st),
        ]], colWidths=[W * 0.88, W * 0.12])
        hdr_row.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#0c1f3a")),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("LINEBELOW",     (0, 0), (-1, -1), 0.5, CYAN),
        ]))

        # Item rows
        item_rows = []
        for it in cat["items"]:
            status = items.get(it["id"], "non_compliant")
            sc_col = STATUS_COLOR.get(status, GRAY)
            sc_bg2 = STATUS_BG.get(status, CARD_BG)
            sl     = STATUS_LABEL.get(status, status)

            badge_st = _style(f"Bdg{it['id']}", fontSize=7, fontName="Helvetica-Bold",
                               textColor=sc_col)
            label_st = _style(f"Lbl{it['id']}", fontSize=8, textColor=WHITE, leading=11)
            desc_st  = _style(f"Dsc{it['id']}", fontSize=7, textColor=GRAY, leading=10,
                               spaceAfter=0)

            badge_cell = Paragraph(sl, badge_st)
            content_cell = [Paragraph(it["label"], label_st),
                            Paragraph(it["desc"],   desc_st)]

            item_rows.append([badge_cell, content_cell])

        items_table = Table(item_rows, colWidths=[W * 0.16, W * 0.84])

        item_ts = [
            ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
            ("ROWBACKGROUNDS",(0, 0), (-1, -1), [CARD_BG, colors.HexColor("#162032")]),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
            ("ALIGN",         (0, 0), (0, -1),  "CENTER"),
            ("VALIGN",        (0, 0), (0, -1),  "MIDDLE"),
        ]
        # Color-coded left border per status
        for row_idx, it in enumerate(cat["items"]):
            status = items.get(it["id"], "non_compliant")
            sc_bg2 = STATUS_BG.get(status, CARD_BG)
            item_ts.append(("BACKGROUND", (0, row_idx), (0, row_idx), sc_bg2))

        items_table.setStyle(TableStyle(item_ts))

        story.append(KeepTogether([hdr_row, items_table]))
        story.append(Spacer(1, 3 * mm))

    # ── DISCLAIMER ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Rapport NIS2 généré par CyberScan le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas un audit légal de conformité.",
        _style("Disc", fontSize=7, textColor=GRAY),
    ))

    doc.build(
        story,
        onFirstPage=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2", user_email),
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2"),
    )
    return buf.getvalue()
