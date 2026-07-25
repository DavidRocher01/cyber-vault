"""theme.py — brand colours, paragraph styles and shared table/section helpers."""

from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ─── Brand colours (dark theme — aligned with pdf_brand.py) ───
COLOR_CRITICAL = colors.HexColor("#f87171")  # RED
COLOR_WARNING = colors.HexColor("#fb923c")  # ORANGE
COLOR_OK = colors.HexColor("#4ade80")  # GREEN
COLOR_PRIMARY = colors.HexColor("#06b6d4")  # CYAN — text only
COLOR_BG = colors.HexColor("#0f172a")  # page background
COLOR_CARD = colors.HexColor("#1e293b")  # card / table header bg
COLOR_BORDER = colors.HexColor("#334155")  # borders
COLOR_MUTED = colors.HexColor("#94a3b8")  # secondary text
COLOR_TEXT = colors.HexColor("#e2e8f0")  # primary text

# Aliases kept for backward compat
COLOR_WHITE = colors.white
COLOR_LIGHT_BORDER = COLOR_BORDER
COLOR_ROW_ALT = COLOR_CARD


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------
def _build_styles() -> dict[str, Any]:
    base = getSampleStyleSheet()

    styles = {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=COLOR_TEXT,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontName="Helvetica",
            fontSize=14,
            textColor=COLOR_MUTED,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_confidential": ParagraphStyle(
            "cover_confidential",
            fontName="Helvetica-Bold",
            fontSize=11,
            textColor=COLOR_WARNING,
            alignment=TA_CENTER,
        ),
        "section_title": ParagraphStyle(
            "section_title",
            fontName="Helvetica-Bold",
            fontSize=13,
            textColor=COLOR_TEXT,
            spaceBefore=18,
            spaceAfter=8,
        ),
        "toc_entry": ParagraphStyle(
            "toc_entry",
            fontName="Helvetica",
            fontSize=11,
            textColor=COLOR_PRIMARY,
            spaceAfter=5,
            leftIndent=12,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_MUTED,
            spaceAfter=4,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_MUTED,
            spaceAfter=5,
            leftIndent=16,
            bulletIndent=4,
        ),
        "label": ParagraphStyle(
            "label",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=COLOR_PRIMARY,
        ),
        "cell": ParagraphStyle(
            "cell",
            fontName="Helvetica",
            fontSize=9,
            textColor=COLOR_MUTED,
        ),
    }
    return styles


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------
def _status_color(status: str) -> colors.Color:
    mapping = {
        "OK": COLOR_OK,
        "WARNING": COLOR_WARNING,
        "CRITICAL": COLOR_CRITICAL,
    }
    return mapping.get(status, colors.HexColor("#64748B"))


def _status_bullet(status: str) -> str:
    """Return a bullet+text string for inline status display (no background fill)."""
    labels = {
        "OK": "● OK",
        "WARNING": "● WARNING",
        "CRITICAL": "● CRITICAL",
    }
    return labels.get(status, f"● {status}")


def _status_inline(status: str) -> Paragraph:
    """Return a Paragraph with colored bullet text — no background coloring."""
    c = _status_color(status)
    st = ParagraphStyle(
        "inline_status",
        fontName="Helvetica-Bold",
        fontSize=10,
        textColor=c,
    )
    return Paragraph(_status_bullet(status), st)


# ---------------------------------------------------------------------------
# Standard table style factory
# ---------------------------------------------------------------------------
def _std_table_style(extra: list | None = None) -> TableStyle:
    """
    Returns the standard dark-theme table style:
    - Header row: COLOR_CARD bg, COLOR_PRIMARY text, bold 10pt
    - Data rows: alternating COLOR_BG / COLOR_CARD
    - No INNERGRID — only BOX + LINEBELOW
    - Padding: top/bottom=8, left/right=12
    """
    base = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_CARD),
        ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        # Data rows alternating
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [COLOR_BG, COLOR_CARD]),
        # Text color for data cells
        ("TEXTCOLOR", (0, 1), (-1, -1), COLOR_TEXT),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        # Borders: box + horizontal separators only
        ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        # Alignment / padding
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]
    if extra:
        base.extend(extra)
    return TableStyle(base)


def _kv_table(rows: list, col_widths: list, extra: list | None = None) -> Table:
    """Construit un tableau au style standard en une seule etape.

    Centralise le couple ``Table(rows, colWidths=...) + setStyle(_std_table_style(...))``
    reproduit dans une vingtaine de sections. ``col_widths`` reste passe
    explicitement pour preserver a l'octet pres le rendu existant.
    """
    t = Table(rows, colWidths=col_widths)
    t.setStyle(_std_table_style(extra))
    return t


# ---------------------------------------------------------------------------
# Section header helper
# ---------------------------------------------------------------------------
def _section_header(num: str | int, title: str, styles: dict[str, Any]) -> list:
    """
    Returns a list of flowables representing a styled section header:
    - Left accent bar (cyan 4mm) + bold title text
    - Thin HR separator
    """
    accent_style = ParagraphStyle(
        "sh_accent",
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=COLOR_TEXT,
    )
    # Accent bar as a tiny filled table cell
    bar_data = [[""]]
    bar_table = Table(bar_data, colWidths=[4 * mm], rowHeights=[0.6 * cm])
    bar_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_PRIMARY),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    title_para = Paragraph(f"{num}. {title}", accent_style)

    header_table = Table(
        [[bar_table, title_para]],
        colWidths=[4 * mm + 6, None],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    return [
        Spacer(1, 0.5 * cm),
        header_table,
        Spacer(1, 0.15 * cm),
        HRFlowable(width="100%", thickness=0.5, color=COLOR_BORDER, spaceAfter=0),
        Spacer(1, 0.3 * cm),
    ]


# ---------------------------------------------------------------------------
# Cover page
# ---------------------------------------------------------------------------
def _kv_styles(suffix):
    """Styles (en-tete, cellule) standards d'un tableau cle/valeur de section."""
    return (
        ParagraphStyle(
            f"th{suffix}",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=COLOR_PRIMARY,
        ),
        ParagraphStyle(
            f"td{suffix}", fontName="Helvetica", fontSize=10, textColor=COLOR_TEXT
        ),
    )


def _not_scanned_table(head_style, cell_style, col_w):
    """Tableau 'Non scanne' affiche quand un module est saute/absent."""
    return Table(
        [[Paragraph("Résultat", head_style)], [Paragraph("Non scanné", cell_style)]],
        colWidths=[col_w],
    )
