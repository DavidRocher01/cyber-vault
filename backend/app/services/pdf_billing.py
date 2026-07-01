"""
Boilerplate partagé des documents de facturation (factures + devis).

Auto-entrepreneur français : TVA non applicable, art. 293 B du CGI.
Palette claire (pour impression) — distincte du thème sombre des rapports
techniques (`pdf_brand.py`).
"""

from __future__ import annotations

from datetime import date

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph

# ── Palette (thème clair) ───────────────────────────────────────────────────────
NAVY = colors.HexColor("#0f172a")
CYAN = colors.HexColor("#06b6d4")
GRAY = colors.HexColor("#64748b")
LGRAY = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")
WHITE = colors.white
BLACK = colors.HexColor("#1e293b")

# ── Émetteur ────────────────────────────────────────────────────────────────────
VENDOR = {
    "name": "David Rocher",
    "status": "Entrepreneur individuel",
    "address": "546 Montée Carriat",
    "city": "01600 Reyrieux, France",
    "siret": "104 009 634 00015",
    "ape": "6202A",
    "email": "contact@rochercybersecurite.com",
    "website": "rochercybersecurite.com",
}

_MONTHS_FR = [
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
]


def _p(text: str, **kw) -> Paragraph:
    """Paragraphe avec un style anonyme construit à la volée."""
    return Paragraph(text, ParagraphStyle("_", **kw))


def _fmt(cents: int) -> str:
    """Montant en centimes → '1 234,56 €'."""
    return f"{cents / 100:,.2f} €".replace(",", " ")


def _date(d: date) -> str:
    """Date → '5 juillet 2026'."""
    return f"{d.day} {_MONTHS_FR[d.month - 1]} {d.year}"
