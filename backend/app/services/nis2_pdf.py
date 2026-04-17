"""
NIS2 Compliance PDF report generator using ReportLab.
Uses shared visual identity from pdf_brand.
"""

from __future__ import annotations

import io
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
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
    STATUS_COLOR, STATUS_LABEL, STATUS_BG,
    draw_page, draw_compliance_cover, score_color, cat_score,
    get_styles,
    section_rule,
)

DOC_TYPE = "nis2"

ROW_A = CARD_BG
ROW_B = colors.HexColor("#162032")


def _st(name, **kw) -> ParagraphStyle:
    d = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2, leading=12)
    d.update(kw)
    return ParagraphStyle(name, **d)


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

    date_str    = updated_at.strftime("%d/%m/%Y à %H:%M") if updated_at else "—"
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"

    all_ids     = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = sum(1 for i in all_ids if items.get(i, "non_compliant") == "compliant")
    partial_n   = sum(1 for i in all_ids if items.get(i, "non_compliant") == "partial")
    nc_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "non_compliant")
    na_n        = sum(1 for i in all_ids if items.get(i, "non_compliant") == "na")

    domain_scores: list[tuple[str, int]] = [
        (cat["label"], cat_score(cat["items"], items))
        for cat in categories
    ]

    # Cover is page 1 (drawn by onFirstPage). Content starts on page 2.
    story: list = [PageBreak()]

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
        pct = cat_score(cat_items, items)
        bar_color = score_color(pct)

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
        pct = cat_score(cat["items"], items)

        # Category header
        hdr_row = Table([[
            Paragraph(cat["label"],
                      _st(f"CH{cat['id']}", fontSize=9, fontName="Helvetica-Bold",
                          textColor=CYAN, leading=13)),
            Paragraph(f"{pct}%",
                      _st(f"CS{cat['id']}", fontSize=8, fontName="Helvetica-Bold",
                          textColor=score_color(pct))),
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
        f"Rapport NIS2 généré par CyberScan le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas un audit légal de conformité.",
        _st("Disc", fontSize=7, textColor=GRAY),
    ))

    def _first_page(c, d):
        draw_compliance_cover(
            c, d,
            doc_type=DOC_TYPE,
            title_line1="Rapport de conformite",
            title_line2="Directive NIS2",
            score=score, score_label=score_label, total=total_items,
            compliant=compliant_n, partial=partial_n, nc=nc_n, na=na_n,
            date_str=date_str,
            domain_scores=domain_scores,
        )

    doc.build(
        story,
        onFirstPage=_first_page,
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2"),
    )
    return buf.getvalue()
