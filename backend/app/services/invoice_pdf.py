"""
Generate a professional PDF invoice.
French auto-entrepreneur compliant: TVA non applicable, art. 293 B du CGI.
"""

from __future__ import annotations

import io
from datetime import date

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

# ── Palette ────────────────────────────────────────────────────────────────────
NAVY = colors.HexColor("#0f172a")
CYAN = colors.HexColor("#06b6d4")
GRAY = colors.HexColor("#64748b")
LGRAY = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")
WHITE = colors.white
BLACK = colors.HexColor("#1e293b")

# ── Vendor ────────────────────────────────────────────────────────────────────
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


def _p(text: str, **kw) -> Paragraph:
    return Paragraph(text, ParagraphStyle("_", **kw))


def _fmt(cents: int) -> str:
    return f"{cents / 100:,.2f} €".replace(",", " ")


def _date(d: date) -> str:
    m = [
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
    return f"{d.day} {m[d.month - 1]} {d.year}"


def generate_invoice_pdf(
    invoice_number: str,
    issue_date: date,
    client_name: str,
    client_email: str,
    client_address: str | None,
    description: str,
    amount_cents: int,
) -> bytes:
    buf = io.BytesIO()
    W, _ = A4
    mg = 16 * mm
    cw = W - 2 * mg

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=mg,
        rightMargin=mg,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    s = []

    half = cw / 2 - 3 * mm
    gap = 6 * mm

    # ══════════════════════════════════════════════════════════════════════════
    # 1. TOP ROW — brand left / FACTURE box right
    # ══════════════════════════════════════════════════════════════════════════
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

    facture_box = Table(
        [
            [
                _p(
                    "<b>FACTURE</b>",
                    fontSize=20,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ]
        ],
        colWidths=[half],
    )
    facture_box.setStyle(
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

    top_row = Table([[brand_box, "", facture_box]], colWidths=[half, gap, half])
    top_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    s.append(top_row)
    s.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 2. SECOND ROW — vendor info left / ref + date right
    # ══════════════════════════════════════════════════════════════════════════
    vendor_info = _p(
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

    ref_info = _p(
        f"<font color='#64748b' size='8'>Référence :</font> <b>{invoice_number}</b><br/>"
        f"<font color='#64748b' size='8'>Date de facturation :</font> {_date(issue_date)}",
        fontSize=8.5,
        fontName="Helvetica",
        textColor=BLACK,
        leading=14,
        alignment=2,
    )

    info_row = Table([[vendor_info, "", ref_info]], colWidths=[half, gap, half])
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
    s.append(info_row)
    s.append(Spacer(1, 6 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 3. CLIENT ROW — label left / client box right
    # ══════════════════════════════════════════════════════════════════════════
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
    s.append(client_row)
    s.append(Spacer(1, 7 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 4. ITEMS TABLE
    # ══════════════════════════════════════════════════════════════════════════
    col_d = cw * 0.70
    col_a = cw * 0.30

    items = Table(
        [
            [
                _p(
                    "Description",
                    fontSize=8.5,
                    fontName="Helvetica-Bold",
                    textColor=BLACK,
                ),
                _p(
                    "Montant TTC",
                    fontSize=8.5,
                    fontName="Helvetica-Bold",
                    textColor=BLACK,
                    alignment=2,
                ),
            ],
            [
                _p(
                    description,
                    fontSize=9,
                    fontName="Helvetica",
                    textColor=BLACK,
                    leading=13,
                ),
                _p(
                    _fmt(amount_cents),
                    fontSize=9,
                    fontName="Helvetica",
                    textColor=BLACK,
                    alignment=2,
                ),
            ],
        ],
        colWidths=[col_d, col_a],
    )
    items.setStyle(
        TableStyle(
            [
                # Header
                ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
                ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("LEFTPADDING", (0, 0), (-1, 0), 10),
                ("RIGHTPADDING", (0, 0), (-1, 0), 10),
                # Data
                ("TOPPADDING", (0, 1), (-1, -1), 11),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 11),
                ("LEFTPADDING", (0, 1), (-1, -1), 10),
                ("RIGHTPADDING", (0, 1), (-1, -1), 10),
                ("LINEBELOW", (0, 1), (-1, -1), 0.5, BORDER),
                # Box
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    s.append(items)
    s.append(Spacer(1, 5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 5. BOTTOM ROW — notes/signature left / totals right
    # ══════════════════════════════════════════════════════════════════════════
    notes_box = Table(
        [
            [
                _p(
                    f"Fait à Reyrieux, le {_date(issue_date)}",
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                ),
            ],
            [
                _p(
                    "<b>Signature</b>",
                    fontSize=8.5,
                    fontName="Helvetica-Bold",
                    textColor=BLACK,
                ),
            ],
            [
                _p("", fontSize=8, fontName="Helvetica", textColor=GRAY),
            ],
        ],
        colWidths=[half],
    )
    notes_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 1), (0, 1), 4),
                ("BOTTOMPADDING", (0, 1), (0, 1), 0),
                ("TOPPADDING", (0, 2), (0, 2), 28),
                ("BOTTOMPADDING", (0, 2), (0, 2), 8),
            ]
        )
    )

    totals_box = Table(
        [
            [
                _p("Total TTC", fontSize=10, fontName="Helvetica-Bold", textColor=NAVY),
                _p(
                    f"<b>{_fmt(amount_cents)}</b>",
                    fontSize=11,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ],
            [
                _p(
                    "TVA non applicable",
                    fontSize=7.5,
                    fontName="Helvetica-Oblique",
                    textColor=GRAY,
                ),
                _p(
                    "art. 293 B du CGI",
                    fontSize=7.5,
                    fontName="Helvetica-Oblique",
                    textColor=GRAY,
                    alignment=2,
                ),
            ],
            [
                _p(
                    "Net à payer",
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                ),
                _p(
                    f"<b>{_fmt(amount_cents)}</b>",
                    fontSize=11,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ],
        ],
        colWidths=[half * 0.55, half * 0.45],
    )
    totals_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEABOVE", (0, 0), (-1, 0), 1.5, CYAN),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
                ("BACKGROUND", (0, 2), (-1, 2), LGRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    bottom_row = Table([[notes_box, "", totals_box]], colWidths=[half, gap, half])
    bottom_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    s.append(bottom_row)
    s.append(Spacer(1, 12 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 6. FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    s.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    s.append(
        _p(
            f"{VENDOR['name']} — SIRET {VENDOR['siret']} — APE {VENDOR['ape']} — "
            f"{VENDOR['email']} — {VENDOR['website']}",
            fontSize=7,
            fontName="Helvetica",
            textColor=GRAY,
            alignment=1,
            leading=10,
        )
    )
    s.append(
        _p(
            "En cas de retard de paiement, une indemnité forfaitaire de recouvrement de 40 € "
            "sera exigible (art. L.441-10 du Code de commerce). Aucun escompte pour paiement anticipé.",
            fontSize=6.5,
            fontName="Helvetica",
            textColor=GRAY,
            alignment=1,
            leading=9,
            spaceBefore=3,
        )
    )

    doc.build(s)
    return buf.getvalue()
