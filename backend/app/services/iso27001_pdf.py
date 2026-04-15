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
    STATUS_COLOR, STATUS_LABEL, STATUS_BG,
    draw_page, draw_compliance_cover, score_color, cat_score,
)

DOC_TYPE   = "iso27001"
VIOLET     = colors.HexColor("#8b5cf6")
VIOLET_DIM = colors.HexColor("#3b1f6e")
VIOLET_BG  = colors.HexColor("#13102a")
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
        (cat["label"], cat_score(cat["items"], items))
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
        pct       = cat_score(cat_items, items)
        bar_color = score_color(pct)
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
        pct = cat_score(cat["items"], items)
        sc  = score_color(pct)

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
        draw_compliance_cover(
            canvas, doc,
            doc_type=DOC_TYPE,
            title_line1="Rapport de conformite",
            title_line2="ISO/IEC 27001:2022",
            score=score, score_label=score_label, total=total_items,
            compliant=compliant_n, partial=partial_n, nc=nc_n, na=na_n,
            date_str=date_str,
            domain_scores=domain_scores,
        )

    def _later_pages(canvas, doc):
        draw_page(canvas, doc, DOC_TYPE, "Conformité ISO 27001:2022", "")

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
    return buf.getvalue()
