"""
Boilerplate partagé des documents de facturation (factures + devis).

Auto-entrepreneur français : TVA non applicable, art. 293 B du CGI.
Palette claire (pour impression) — distincte du thème sombre des rapports
techniques (`pdf_brand.py`).
"""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

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


# ── Blocs partagés facture / devis ──────────────────────────────────────────────
# Ces builders factorisent la mise en page strictement identique entre
# invoice_pdf.py et quote_pdf.py (en-tête de marque, bloc émetteur, bloc client,
# pied de page d'identité). Seul le contenu spécifique (label du document, réf,
# lignes d'items, totaux, mentions légales) reste dans chaque générateur.


def new_billing_doc(buf: io.BytesIO) -> tuple[SimpleDocTemplate, float, float, float]:
    """Crée le SimpleDocTemplate commun et renvoie (doc, cw, half, gap)."""
    page_w, _ = A4
    mg = 16 * mm
    cw = page_w - 2 * mg
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=mg,
        rightMargin=mg,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    half = cw / 2 - 3 * mm
    gap = 6 * mm
    return doc, cw, half, gap


def build_brand_header(doc_label: str, half: float, gap: float) -> Table:
    """En-tête : marque (gauche) + encadré du type de document (droite)."""
    brand_box = Table(
        [
            [
                _p(
                    "<b>Rocher Cybersécurité</b>",
                    fontSize=18,
                    fontName="Helvetica-Bold",
                    textColor=WHITE,
                    leading=22,
                ),
                _p(
                    "<font color='#06b6d4'>●</font>",
                    fontSize=24,
                    fontName="Helvetica-Bold",
                    textColor=CYAN,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half * 0.7, half * 0.3],
    )
    brand_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    label_box = Table(
        [
            [
                _p(
                    f"<b>{doc_label}</b>",
                    fontSize=20,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half],
    )
    label_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, NAVY),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

    top_row = Table([[brand_box, "", label_box]], colWidths=[half, gap, half])
    top_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return top_row


def build_vendor_info() -> Paragraph:
    """Bloc identité de l'émetteur (colonne gauche de la ligne d'infos)."""
    return _p(
        f"<b>{VENDOR['name']}</b><br/>"
        f"{VENDOR['status']}<br/>"
        f"{VENDOR['address']}<br/>"
        f"{VENDOR['city']}<br/>"
        f"SIRET : {VENDOR['siret']}<br/>"
        f"APE : {VENDOR['ape']}<br/>"
        f"{VENDOR['email']}",
        fontSize=8.5,
        fontName="Helvetica",
        textColor=BLACK,
        leading=13,
    )


def build_info_row(ref_info: Paragraph, half: float, gap: float) -> Table:
    """Ligne d'infos : émetteur (gauche) + bloc référence/date (droite)."""
    info_row = Table([[build_vendor_info(), "", ref_info]], colWidths=[half, gap, half])
    info_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return info_row


def build_client_row(
    client_name: str,
    client_email: str,
    client_address: str | None,
    half: float,
    gap: float,
) -> Table:
    """Ligne client : libellé émetteur (gauche) + encadré coordonnées client (droite)."""
    vendor_label = Table(
        [
            [
                _p(
                    f"<b>{VENDOR['name']}</b>",
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                ),
            ]
        ],
        colWidths=[half],
    )
    vendor_label.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )

    addr_lines = f"<b>{client_name}</b><br/>{client_email}"
    if client_address:
        addr_lines += f"<br/>{client_address}"

    client_box = Table(
        [
            [
                _p(
                    addr_lines,
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                    leading=13,
                ),
            ]
        ],
        colWidths=[half],
    )
    client_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LGRAY),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )

    client_row = Table([[vendor_label, "", client_box]], colWidths=[half, gap, half])
    client_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    return client_row


def build_footer_identity() -> Paragraph:
    """Ligne d'identité légale du pied de page (SIRET / APE / contact)."""
    return _p(
        f"{VENDOR['name']} — SIRET {VENDOR['siret']} — APE {VENDOR['ape']} — "
        f"{VENDOR['email']} — {VENDOR['website']}",
        fontSize=7,
        fontName="Helvetica",
        textColor=GRAY,
        alignment=1,
        leading=10,
    )
