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


def _style(name, **kwargs) -> ParagraphStyle:
    defaults = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2)
    defaults.update(kwargs)
    return ParagraphStyle(name, **defaults)


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

    title_st   = _style("T", fontSize=22, fontName="Helvetica-Bold")
    sub_st     = _style("S", fontSize=10, textColor=GRAY)
    section_st = st["section"]
    body_st    = _style("B", fontSize=9, textColor=colors.HexColor("#cbd5e1"))
    small_st   = _style("Sm", fontSize=8, textColor=GRAY)

    story = []

    # ── Score hero ──────────────────────────────────────────────────────────
    date_str = updated_at.strftime("%d/%m/%Y") if updated_at else datetime.utcnow().strftime("%d/%m/%Y")

    if score >= 80:
        score_color = GREEN
        level = "Conforme"
    elif score >= 50:
        score_color = YELLOW
        level = "En cours"
    else:
        score_color = RED
        level = "Non conforme"

    score_st = _style("ScD", fontSize=32, fontName="Helvetica-Bold", textColor=score_color)
    level_st = _style("LvD", fontSize=13, fontName="Helvetica-Bold", textColor=score_color)

    # Count items by status
    total_items = sum(len(cat["items"]) for cat in categories)
    compliant_n = sum(1 for v in items.values() if v == "compliant")
    partial_n   = sum(1 for v in items.values() if v == "partial")
    nc_n        = sum(1 for v in items.values() if v == "non_compliant")
    na_n        = sum(1 for v in items.values() if v == "na")

    score_table = Table([[
        Paragraph(f"{score}%", score_st),
        Paragraph(
            f"{level}<br/>"
            f"<font size='9' color='#4ade80'>&#10003; {compliant_n} conformes</font>  "
            f"<font size='9' color='#facc15'>~ {partial_n} partiels</font>  "
            f"<font size='9' color='#f87171'>&#10007; {nc_n} non-conformes</font>  "
            f"<font size='9' color='#94a3b8'>&#8212; {na_n} N/A</font><br/>"
            f"<font size='8' color='#64748b'>{total_items} critères évalués au total</font>",
            level_st,
        ),
    ]], colWidths=[W * 0.2, W * 0.8])
    score_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 16),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 16),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(score_table)
    story.append(Spacer(1, 6 * mm))

    # ── Category summary bar ─────────────────────────────────────────────────
    story.append(Paragraph("Résumé par catégorie", section_st))
    story.append(section_rule(W, DOC_TYPE))

    cat_rows = [["Catégorie", "Conformes", "Partiels", "Non-conformes", "N/A"]]
    for cat in categories:
        cat_items = cat["items"]
        c = sum(1 for it in cat_items if items.get(it["id"]) == "compliant")
        p = sum(1 for it in cat_items if items.get(it["id"]) == "partial")
        n = sum(1 for it in cat_items if items.get(it["id"]) == "non_compliant")
        na = sum(1 for it in cat_items if items.get(it["id"]) == "na")
        cat_rows.append([cat["label"], str(c), str(p), str(n), str(na)])

    cat_table = Table(cat_rows, colWidths=[W * 0.40, W * 0.15, W * 0.15, W * 0.18, W * 0.12])
    cat_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), DARK_BG),
        ("BACKGROUND",    (0, 1), (-1, -1), CARD_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), GRAY),
        ("TEXTCOLOR",     (1, 1), (1, -1), GREEN),
        ("TEXTCOLOR",     (2, 1), (2, -1), YELLOW),
        ("TEXTCOLOR",     (3, 1), (3, -1), RED),
        ("TEXTCOLOR",     (4, 1), (4, -1), GRAY),
        ("TEXTCOLOR",     (0, 1), (0, -1), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME",      (1, 1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 6 * mm))

    # ── Detailed checklist ───────────────────────────────────────────────────
    story.append(Paragraph("Détail des critères", section_st))
    story.append(section_rule(W, DOC_TYPE))

    for cat in categories:
        story.append(Paragraph(cat["label"], _style(
            f"Cat{cat['id']}", fontSize=10, fontName="Helvetica-Bold",
            textColor=CYAN, spaceBefore=6, spaceAfter=3,
        )))
        rows = [["Statut", "Critère"]]
        for it in cat["items"]:
            status = items.get(it["id"], "non_compliant")
            sc = STATUS_COLOR.get(status, GRAY)
            sl = STATUS_LABEL.get(status, status)
            sev_st = _style(f"I{it['id']}", fontSize=8, fontName="Helvetica-Bold", textColor=sc)
            rows.append([
                Paragraph(sl, sev_st),
                Paragraph(it["label"], body_st),
            ])
        t = Table(rows, colWidths=[W * 0.18, W * 0.82])
        t.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), DARK_BG),
            ("BACKGROUND",    (0, 1), (-1, -1), CARD_BG),
            ("TEXTCOLOR",     (0, 0), (-1, 0), GRAY),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)
        story.append(Spacer(1, 2 * mm))

    # ── Disclaimer ───────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Rapport NIS2 généré par CyberScan le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas un audit légal de conformité.",
        small_st,
    ))

    doc.build(
        story,
        onFirstPage=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2", user_email),
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Conformité NIS2"),
    )
    return buf.getvalue()
