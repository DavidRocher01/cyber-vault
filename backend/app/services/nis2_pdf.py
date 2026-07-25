"""
NIS2 Compliance PDF report generator using ReportLab.
Mise en page partagée via pdf_compliance ; ce module ne porte que le style NIS2.
"""

from __future__ import annotations

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.units import mm

from app.services.pdf_brand import BORDER, CYAN, get_styles, section_rule
from app.services.pdf_compliance import ComplianceStyle, generate_compliance_pdf

DOC_TYPE = "nis2"

_STYLE = ComplianceStyle(
    doc_type=DOC_TYPE,
    top_margin=25 * mm,
    bottom_margin=20 * mm,
    section_style=get_styles(DOC_TYPE)["section"],
    make_section_rule=lambda w: section_rule(w, DOC_TYPE),
    title_summary="Résumé par catégorie",
    title_detail="Détail des critères",
    col1_header="Catégorie",
    nc_header="✗ N.Conf.",
    summary_col_ratios=(0.36, 0.30, 0.085, 0.085, 0.095, 0.075),
    summary_header_bg=colors.HexColor("#0c1422"),
    summary_pad=6,
    summary_has_fontsize_rule=True,
    summary_linebelow=BORDER,
    summary_line_before=None,
    bar_h=6,
    count_font=8,
    count_align=None,
    spacer_after_summary=7 * mm,
    cat_header_bg=colors.HexColor("#0c1f3a"),
    cat_accent=CYAN,
    cat_label_font=9,
    cat_label_leading=13,
    cat_header_ratios=(0.88, 0.12),
    cat_score_font=8,
    cat_score_align=None,
    cat_pad=(8, 8, 10, 10),
    cat_line_before=None,
    cat_line_below=(1, CYAN),
    badge_boxed=False,
    item_ratios=(0.16, 0.84),
    spacer_after_cat=3 * mm,
    disclaimer=(
        "Rapport NIS2 généré par Rocher Cybersécurité le {date} UTC — "
        "Ce rapport est fourni à titre indicatif et ne constitue pas un audit légal de conformité."
    ),
    cover_title1="Rapport de conformite",
    cover_title2="Directive NIS2",
    later_page_title="Conformité NIS2",
)


def generate_nis2_pdf(
    categories: list[dict],
    items: dict[str, str],
    score: int,
    updated_at: datetime | None,
    user_email: str,
) -> bytes:
    return generate_compliance_pdf(_STYLE, categories, items, score, updated_at, user_email)
