"""
ISO 27001:2022 Compliance PDF — premium violet design.
Mise en page partagée via pdf_compliance ; ce module ne porte que le style ISO.
"""

from __future__ import annotations

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import HRFlowable

from app.services.pdf_compliance import ComplianceStyle, generate_compliance_pdf

DOC_TYPE = "iso27001"
VIOLET = colors.HexColor("#8b5cf6")
VIOLET_DIM = colors.HexColor("#3b1f6e")
VIOLET_BG = colors.HexColor("#13102a")

_SECTION_STYLE = ParagraphStyle(
    "iso_section",
    fontName="Helvetica-Bold",
    textColor=VIOLET,
    fontSize=13,
    spaceBefore=4,
    spaceAfter=4,
    leading=12,
)

_STYLE = ComplianceStyle(
    doc_type=DOC_TYPE,
    top_margin=22 * mm,
    bottom_margin=18 * mm,
    section_style=_SECTION_STYLE,
    make_section_rule=lambda w: HRFlowable(width=w, thickness=1.2, color=VIOLET, spaceAfter=6),
    title_summary="Résumé par domaine",
    title_detail="Détail des contrôles",
    col1_header="Domaine",
    nc_header="✗ N.C.",
    summary_col_ratios=(0.34, 0.30, 0.09, 0.09, 0.10, 0.08),
    summary_header_bg=colors.HexColor("#0c0f1a"),
    summary_pad=7,
    summary_has_fontsize_rule=False,
    summary_linebelow=VIOLET,
    summary_line_before=VIOLET_DIM,
    bar_h=8,
    count_font=9,
    count_align=1,
    spacer_after_summary=8 * mm,
    cat_header_bg=VIOLET_BG,
    cat_accent=VIOLET,
    cat_label_font=10,
    cat_label_leading=14,
    cat_header_ratios=(0.85, 0.15),
    cat_score_font=9,
    cat_score_align=2,
    cat_pad=(9, 9, 12, 10),
    cat_line_before=VIOLET,
    cat_line_below=(0.8, VIOLET),
    badge_boxed=True,
    item_ratios=(0.18, 0.82),
    spacer_after_cat=4 * mm,
    disclaimer=(
        "Rapport ISO 27001:2022 généré par Rocher Cybersécurité le {date} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas une certification ISO/IEC 27001."
    ),
    cover_title1="Rapport de conformite",
    cover_title2="ISO/IEC 27001:2022",
    later_page_title="Conformité ISO 27001:2022",
)


def generate_iso27001_pdf(
    categories: list[dict],
    items: dict[str, str],
    score: int,
    updated_at: datetime | None,
    user_email: str,
) -> bytes:
    return generate_compliance_pdf(_STYLE, categories, items, score, updated_at, user_email)
