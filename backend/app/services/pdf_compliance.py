"""
Générateur PDF de conformité partagé (NIS2 + ISO 27001).

Les deux rapports partageaient ~300 lignes de mise en page identique
(tableau de synthèse par domaine + checklist détaillée). Cette logique vit
désormais ici, paramétrée par un ComplianceStyle qui capture les seules
divergences visuelles réelles (accent cyan NIS2 vs violet ISO, hauteur de
barre, badge encadré ou non, marges, libellés, texte de disclaimer, page de
garde). nis2_pdf.py et iso27001_pdf.py ne sont plus que de fines
configurations.
"""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.pdf_brand import (
    BORDER,
    CARD_BG,
    GRAY,
    GREEN,
    RED,
    STATUS_BG,
    STATUS_COLOR,
    STATUS_LABEL,
    WHITE,
    YELLOW,
    cat_score,
    draw_compliance_cover,
    draw_page,
    score_color,
)

ROW_A = CARD_BG
ROW_B = colors.HexColor("#162032")
_EMPTY_BAR = colors.HexColor("#1e293b")


@dataclass(frozen=True)
class ComplianceStyle:
    """Toutes les divergences visuelles entre les rapports NIS2 et ISO 27001."""

    doc_type: str
    top_margin: float
    bottom_margin: float
    # Titres de section
    section_style: ParagraphStyle
    make_section_rule: Callable[[float], Flowable]
    title_summary: str
    title_detail: str
    # Tableau de synthèse
    col1_header: str
    nc_header: str
    summary_col_ratios: tuple[float, ...]
    summary_header_bg: colors.Color
    summary_pad: int
    summary_has_fontsize_rule: bool
    summary_linebelow: colors.Color
    summary_line_before: colors.Color | None
    bar_h: int
    count_font: int
    count_align: int | None
    spacer_after_summary: float
    # Checklist détaillée
    cat_header_bg: colors.Color
    cat_accent: colors.Color
    cat_label_font: int
    cat_label_leading: int
    cat_header_ratios: tuple[float, float]
    cat_score_font: int
    cat_score_align: int | None
    cat_pad: tuple[int, int, int, int]  # top, bottom, left, right
    cat_line_before: colors.Color | None
    cat_line_below: tuple[float, colors.Color]
    badge_boxed: bool
    item_ratios: tuple[float, float]
    spacer_after_cat: float
    # Disclaimer + page de garde
    disclaimer: str
    cover_title1: str
    cover_title2: str
    later_page_title: str


def _st(name: str, **kw) -> ParagraphStyle:
    d = dict(fontName="Helvetica", textColor=WHITE, fontSize=9, spaceAfter=2, leading=12)
    d.update(kw)
    return ParagraphStyle(name, **d)


def _progress_bar(pct: int, bar_w: float, bar_h: int, bar_color: colors.Color) -> Table:
    """Barre de progression : cellule pleine / vide selon pct (identique NIS2/ISO)."""
    zero_pad = [
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]
    if pct <= 0:
        bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
        bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), _EMPTY_BAR), *zero_pad]))
    elif pct >= 100:
        bar = Table([[""]], colWidths=[bar_w], rowHeights=[bar_h])
        bar.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bar_color), *zero_pad]))
    else:
        filled = max(bar_w * pct / 100, 0)
        empty = bar_w - filled
        bar = Table([["", ""]], colWidths=[filled, empty], rowHeights=[bar_h])
        bar.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), bar_color),
                    ("BACKGROUND", (1, 0), (1, 0), _EMPTY_BAR),
                    *zero_pad,
                ]
            )
        )
    return bar


def _count(status: str, all_ids: list[str], items: dict[str, str]) -> int:
    return sum(1 for i in all_ids if items.get(i, "non_compliant") == status)


def _summary_table(cfg: ComplianceStyle, w: float, categories: list[dict], items: dict) -> Table:
    hdr = _st("TH", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)
    col_w = [w * r for r in cfg.summary_col_ratios]

    rows = [
        [
            Paragraph(cfg.col1_header, hdr),
            Paragraph("Score", hdr),
            Paragraph("✓ Conf.", _st("H1", fontSize=8, fontName="Helvetica-Bold", textColor=GREEN)),
            Paragraph(
                "~ Part.", _st("H2", fontSize=8, fontName="Helvetica-Bold", textColor=YELLOW)
            ),
            Paragraph(
                cfg.nc_header, _st("H3", fontSize=8, fontName="Helvetica-Bold", textColor=RED)
            ),
            Paragraph("— N/A", _st("H4", fontSize=8, fontName="Helvetica-Bold", textColor=GRAY)),
        ]
    ]

    def _cnt_para(name: str, value: int, color: colors.Color) -> Paragraph:
        kw = dict(fontSize=cfg.count_font, fontName="Helvetica-Bold", textColor=color)
        if cfg.count_align is not None:
            kw["alignment"] = cfg.count_align
        return Paragraph(str(value), _st(name, **kw))

    for cat in categories:
        cat_items = cat["items"]
        c = _count("compliant", [it["id"] for it in cat_items], items)
        p = _count("partial", [it["id"] for it in cat_items], items)
        n = _count("non_compliant", [it["id"] for it in cat_items], items)
        na = _count("na", [it["id"] for it in cat_items], items)
        pct = cat_score(cat_items, items)
        bar_color = score_color(pct)
        bar = _progress_bar(pct, w * 0.30 - 16, cfg.bar_h, bar_color)

        rows.append(
            [
                Paragraph(cat["label"], _st(f"CL{cat['id']}", fontSize=8, textColor=WHITE)),
                [
                    bar,
                    Paragraph(
                        f"{pct}%",
                        _st(
                            f"BP{cat['id']}",
                            fontSize=7,
                            fontName="Helvetica-Bold",
                            textColor=bar_color,
                            spaceBefore=2,
                        ),
                    ),
                ],
                _cnt_para(f"CC{cat['id']}", c, GREEN),
                _cnt_para(f"CP{cat['id']}", p, YELLOW),
                _cnt_para(f"CN{cat['id']}", n, RED),
                _cnt_para(f"CA{cat['id']}", na, GRAY),
            ]
        )

    table = Table(rows, colWidths=col_w)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), cfg.summary_header_bg),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [ROW_A, ROW_B]),
        ("TOPPADDING", (0, 0), (-1, -1), cfg.summary_pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), cfg.summary_pad),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
        ("ALIGN", (2, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 1, cfg.summary_linebelow),
    ]
    if cfg.summary_has_fontsize_rule:
        style.insert(2, ("FONTSIZE", (0, 0), (-1, -1), 8))
    if cfg.summary_line_before is not None:
        style.append(("LINEBEFORE", (0, 1), (0, -1), 3, cfg.summary_line_before))
    table.setStyle(TableStyle(style))
    return table


def _detail_block(cfg: ComplianceStyle, w: float, cat: dict, items: dict) -> KeepTogether:
    pct = cat_score(cat["items"], items)

    score_kw = dict(
        fontSize=cfg.cat_score_font, fontName="Helvetica-Bold", textColor=score_color(pct)
    )
    if cfg.cat_score_align is not None:
        score_kw["alignment"] = cfg.cat_score_align

    hdr_row = Table(
        [
            [
                Paragraph(
                    cat["label"],
                    _st(
                        f"CH{cat['id']}",
                        fontSize=cfg.cat_label_font,
                        fontName="Helvetica-Bold",
                        textColor=cfg.cat_accent,
                        leading=cfg.cat_label_leading,
                    ),
                ),
                Paragraph(f"{pct}%", _st(f"CS{cat['id']}", **score_kw)),
            ]
        ],
        colWidths=[w * cfg.cat_header_ratios[0], w * cfg.cat_header_ratios[1]],
    )
    top, bottom, left, right = cfg.cat_pad
    hdr_style = [
        ("BACKGROUND", (0, 0), (-1, -1), cfg.cat_header_bg),
        ("TOPPADDING", (0, 0), (-1, -1), top),
        ("BOTTOMPADDING", (0, 0), (-1, -1), bottom),
        ("LEFTPADDING", (0, 0), (-1, -1), left),
        ("RIGHTPADDING", (0, 0), (-1, -1), right),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("LINEBELOW", (0, 0), (-1, -1), cfg.cat_line_below[0], cfg.cat_line_below[1]),
    ]
    if cfg.cat_line_before is not None:
        hdr_style.append(("LINEBEFORE", (0, 0), (0, 0), 4, cfg.cat_line_before))
    hdr_row.setStyle(TableStyle(hdr_style))

    item_rows = []
    item_ts = []
    for row_idx, it in enumerate(cat["items"]):
        status = items.get(it["id"], "non_compliant")
        sc_col = STATUS_COLOR.get(status, GRAY)
        sl = STATUS_LABEL.get(status, status)

        if cfg.badge_boxed:
            badge = Table(
                [
                    [
                        Paragraph(
                            sl,
                            _st(
                                f"Bdg{it['id']}",
                                fontSize=7,
                                fontName="Helvetica-Bold",
                                textColor=sc_col,
                                alignment=1,
                            ),
                        )
                    ]
                ],
                colWidths=[26 * mm],
            )
            badge.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), STATUS_BG.get(status, CARD_BG)),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 3),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                        ("BOX", (0, 0), (-1, -1), 0.7, sc_col),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ]
                )
            )
            badge_cell: object = badge
        else:
            badge_cell = Paragraph(
                sl,
                _st(f"Bdg{it['id']}", fontSize=7, fontName="Helvetica-Bold", textColor=sc_col),
            )

        content_cell = [
            Paragraph(
                it["label"],
                _st(
                    f"Lb{it['id']}",
                    fontSize=8,
                    fontName="Helvetica-Bold",
                    textColor=WHITE,
                    leading=11,
                ),
            ),
            Paragraph(
                it["desc"],
                _st(f"Dc{it['id']}", fontSize=7, textColor=GRAY, leading=10, spaceAfter=0),
            ),
        ]
        item_rows.append([badge_cell, content_cell])
        item_ts.append(("BACKGROUND", (0, row_idx), (0, row_idx), STATUS_BG.get(status, CARD_BG)))

    items_table = Table(item_rows, colWidths=[w * cfg.item_ratios[0], w * cfg.item_ratios[1]])
    items_table.setStyle(
        TableStyle(
            [
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [ROW_A, ROW_B]),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("VALIGN", (0, 0), (0, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.3, BORDER),
                *item_ts,
            ]
        )
    )
    return KeepTogether([hdr_row, items_table])


def generate_compliance_pdf(
    cfg: ComplianceStyle,
    categories: list[dict],
    items: dict[str, str],
    score: int,
    updated_at: datetime | None,
    user_email: str,
) -> bytes:
    buf = io.BytesIO()
    w = A4[0] - 30 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=cfg.top_margin,
        bottomMargin=cfg.bottom_margin,
    )

    date_str = (
        updated_at.strftime("%d/%m/%Y à %H:%M")
        if updated_at
        else datetime.now(UTC).strftime("%d/%m/%Y à %H:%M")
    )
    score_label = "Conforme" if score >= 80 else "En cours" if score >= 50 else "Non conforme"

    all_ids = [it["id"] for cat in categories for it in cat["items"]]
    total_items = len(all_ids)
    compliant_n = _count("compliant", all_ids, items)
    partial_n = _count("partial", all_ids, items)
    nc_n = _count("non_compliant", all_ids, items)
    na_n = _count("na", all_ids, items)

    domain_scores: list[tuple[str, int]] = [
        (cat["label"], cat_score(cat["items"], items)) for cat in categories
    ]

    # La page de garde est la page 1 (dessinée par onFirstPage). Le contenu commence page 2.
    story: list = [PageBreak()]

    story.append(Paragraph(cfg.title_summary, cfg.section_style))
    story.append(cfg.make_section_rule(w))
    story.append(_summary_table(cfg, w, categories, items))
    story.append(Spacer(1, cfg.spacer_after_summary))

    story.append(Paragraph(cfg.title_detail, cfg.section_style))
    story.append(cfg.make_section_rule(w))
    for cat in categories:
        story.append(_detail_block(cfg, w, cat, items))
        story.append(Spacer(1, cfg.spacer_after_cat))

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=w, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(
        Paragraph(
            cfg.disclaimer.format(date=datetime.now(UTC).strftime("%d/%m/%Y à %H:%M")),
            _st("Disc", fontSize=7, textColor=GRAY),
        )
    )

    def _first_page(canvas, d):
        draw_compliance_cover(
            canvas,
            d,
            doc_type=cfg.doc_type,
            title_line1=cfg.cover_title1,
            title_line2=cfg.cover_title2,
            score=score,
            score_label=score_label,
            total=total_items,
            compliant=compliant_n,
            partial=partial_n,
            nc=nc_n,
            na=na_n,
            date_str=date_str,
            domain_scores=domain_scores,
        )

    def _later_pages(canvas, d):
        draw_page(canvas, d, cfg.doc_type, cfg.later_page_title)

    doc.build(story, onFirstPage=_first_page, onLaterPages=_later_pages)
    return buf.getvalue()
