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
    "compliant":     colors.HexColor("#052e16"),
    "partial":       colors.HexColor("#1c1400"),
    "non_compliant": colors.HexColor("#2d0a0a"),
    "na":            colors.HexColor("#0f172a"),
}

ROW_A = CARD_BG
ROW_B = colors.HexColor("#162032")


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
    story = []

    date_str    = updated_at.strftime("%d/%m/%Y à %H:%M") if updated_at else "—"
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"
    sc          = _score_color(score)
    sc_bg       = _score_bg(score)

    all_ids     = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = sum(1 for i in all_ids if items.get(i, "non_compliant") == "compliant")
    partial_n   = sum(1 for i in all_ids if items.get(i, "non_compliant") == "partial")
    nc_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "non_compliant")
    na_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "na")

    # ── SCORE HERO ──────────────────────────────────────────────────────────────
    # Row 1: score % | label + date
    # Row 2: 4 KPI cells (spanning right column)

    score_pct_st  = _st("ScP", fontSize=42, fontName="Helvetica-Bold", textColor=sc, leading=46)
    score_lbl_st  = _st("ScL", fontSize=13, fontName="Helvetica-Bold", textColor=sc, leading=18)
    date_st       = _st("ScD", fontSize=8,  textColor=GRAY, leading=11)
    total_st      = _st("ScT", fontSize=8,  textColor=GRAY, leading=11)

    # KPI cells inside a 1×4 sub-table
    kpi_col_w = W * 0.65 / 4

    def kpi_para(val: int, label: str, color) -> list:
        return [
            Paragraph(str(val), _st(f"KV{label}", fontSize=20, fontName="Helvetica-Bold",
                                    textColor=color, leading=24)),
            Paragraph(label,    _st(f"KL{label}", fontSize=7,  textColor=GRAY, leading=10)),
        ]

    kpi_table = Table(
        [[kpi_para(compliant_n, "Conformes", GREEN),
          kpi_para(partial_n,   "Partiels",  YELLOW),
          kpi_para(nc_n,        "Non conf.", RED),
          kpi_para(na_n,        "N/A",       GRAY)]],
        colWidths=[kpi_col_w] * 4,
    )
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), colors.HexColor("#052e16")),
        ("BACKGROUND",    (1, 0), (1, 0), colors.HexColor("#1c1400")),
        ("BACKGROUND",    (2, 0), (2, 0), colors.HexColor("#2d0a0a")),
        ("BACKGROUND",    (3, 0), (3, 0), colors.HexColor("#0f172a")),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LINEAFTER",     (0, 0), (2, 0),   0.5, BORDER),
    ]))

    right_content = [
        Paragraph(score_label, score_lbl_st),
        Spacer(1, 3),
        Paragraph(f"Mis à jour le {date_str}", date_st),
        Spacer(1, 8),
        kpi_table,
        Spacer(1, 4),
        Paragraph(f"{total_items} critères évalués au total", total_st),
    ]

    hero = Table(
        [[Paragraph(f"{score}%", score_pct_st), right_content]],
        colWidths=[W * 0.25, W * 0.75],
    )
    hero.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
        ("BACKGROUND",    (0, 0), (0, 0),   sc_bg),
        ("TOPPADDING",    (0, 0), (-1, -1), 18),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 18),
        ("LEFTPADDING",   (0, 0), (-1, -1), 20),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("VALIGN",        (0, 0), (0, 0),   "MIDDLE"),
        ("VALIGN",        (1, 0), (1, 0),   "TOP"),
        ("LINEAFTER",     (0, 0), (0, 0),   1, BORDER),
    ]))
    story.append(hero)
    story.append(Spacer(1, 7 * mm))

    # ── CATEGORY SUMMARY ────────────────────────────────────────────────────────
    story.append(Paragraph("Résumé par catégorie", st["section"]))
    story.append(section_rule(W, DOC_TYPE))

    hdr = _st("TH", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)
    col_w = [W * 0.36, W * 0.30, W * 0.085, W * 0.085, W * 0.095, W * 0.075]

    summary_rows = [[
        Paragraph("Catégorie",       hdr),
        Paragraph("Score",           hdr),
        Paragraph("✓ Conf.",         _st("H1", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
        Paragraph("~ Part.",         _st("H2", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)),
        Paragraph("✗ N.Conf.",       _st("H3", fontSize=8, fontName="Helvetica-Bold", textColor=RED)),
        Paragraph("— N/A",           _st("H4", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
    ]]

    for cat in categories:
        cat_items = cat["items"]
        c  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "compliant")
        p  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "partial")
        n  = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "non_compliant")
        na = sum(1 for it in cat_items if items.get(it["id"], "non_compliant") == "na")
        pct = _cat_score(cat_items, items)
        bar_color = _score_color(pct)

        # Progress bar as a 2-col table (filled + empty)
        bar_w = W * 0.30 - 16  # subtract padding
        bar_h = 6
        filled = max(bar_w * pct / 100, 0)
        empty  = bar_w - filled

        if pct <= 0:
            bar = Table([[""]],  colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#1e293b")),
                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
        elif pct >= 100:
            bar = Table([[""]],  colWidths=[bar_w], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), bar_color),
                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))
        else:
            bar = Table([["", ""]], colWidths=[filled, empty], rowHeights=[bar_h])
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0), bar_color),
                ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#1e293b")),
                ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]))

        bar_cell = [
            bar,
            Paragraph(f"{pct}%", _st(f"BP{cat['id']}", fontSize=7, fontName="Helvetica-Bold",
                                      textColor=bar_color, spaceBefore=2)),
        ]

        summary_rows.append([
            Paragraph(cat["label"], _st(f"CL{cat['id']}", fontSize=8, textColor=WHITE)),
            bar_cell,
            Paragraph(str(c),  _st(f"CC{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
            Paragraph(str(p),  _st(f"CP{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)),
            Paragraph(str(n),  _st(f"CN{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=RED)),
            Paragraph(str(na), _st(f"CA{cat['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
        ])

    summary_table = Table(summary_rows, colWidths=col_w)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND",     (0, 0), (-1, 0),   colors.HexColor("#0c1422")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),  [ROW_A, ROW_B]),
        ("FONTSIZE",       (0, 0), (-1, -1),  8),
        ("TOPPADDING",     (0, 0), (-1, -1),  6),
        ("BOTTOMPADDING",  (0, 0), (-1, -1),  6),
        ("LEFTPADDING",    (0, 0), (-1, -1),  8),
        ("RIGHTPADDING",   (0, 0), (-1, -1),  8),
        ("GRID",           (0, 0), (-1, -1),  0.3, BORDER),
        ("ALIGN",          (2, 0), (-1, -1),  "CENTER"),
        ("VALIGN",         (0, 0), (-1, -1),  "MIDDLE"),
        ("LINEBELOW",      (0, 0), (-1, 0),   1, BORDER),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 7 * mm))

    # ── DETAILED CHECKLIST ───────────────────────────────────────────────────────
    story.append(Paragraph("Détail des critères", st["section"]))
    story.append(section_rule(W, DOC_TYPE))

    for cat in categories:
        pct = _cat_score(cat["items"], items)

        # Category header
        hdr_row = Table([[
            Paragraph(cat["label"],
                      _st(f"CH{cat['id']}", fontSize=9, fontName="Helvetica-Bold",
                          textColor=CYAN, leading=13)),
            Paragraph(f"{pct}%",
                      _st(f"CS{cat['id']}", fontSize=8, fontName="Helvetica-Bold",
                          textColor=_score_color(pct))),
        ]], colWidths=[W * 0.88, W * 0.12])
        hdr_row.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#0c1f3a")),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
            ("LINEBELOW",     (0, 0), (-1, -1), 1, CYAN),
        ]))

        # Items
        item_rows = []
        for it in cat["items"]:
            status = items.get(it["id"], "non_compliant")
            sc_col = STATUS_COLOR.get(status, GRAY)
            sl     = STATUS_LABEL.get(status, status)

            badge_cell   = Paragraph(sl, _st(f"Bdg{it['id']}", fontSize=7,
                                             fontName="Helvetica-Bold", textColor=sc_col))
            content_cell = [
                Paragraph(it["label"], _st(f"Lb{it['id']}",  fontSize=8,
                                           fontName="Helvetica-Bold", textColor=WHITE, leading=11)),
                Paragraph(it["desc"],  _st(f"Dc{it['id']}",  fontSize=7,
                                           textColor=GRAY, leading=10, spaceAfter=0)),
            ]
            item_rows.append([badge_cell, content_cell])

        items_table = Table(item_rows, colWidths=[W * 0.16, W * 0.84])

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
        ]
        for row_idx, it in enumerate(cat["items"]):
            status = items.get(it["id"], "non_compliant")
            ts.append(("BACKGROUND", (0, row_idx), (0, row_idx),
                        STATUS_BG.get(status, CARD_BG)))

        items_table.setStyle(TableStyle(ts))
        story.append(KeepTogether([hdr_row, items_table]))
        story.append(Spacer(1, 3 * mm))

    # ── DISCLAIMER ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Rapport NIS2 généré par CyberScan le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas un audit légal de conformité.",
        _st("Disc", fontSize=7, textColor=GRAY),
    ))

    doc.build(
        story,
        onFirstPage=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2", user_email),
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2"),
    )
    return buf.getvalue()
