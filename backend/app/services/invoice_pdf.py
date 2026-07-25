"""
Generate a professional PDF invoice.
French auto-entrepreneur compliant: TVA non applicable, art. 293 B du CGI.
"""

from __future__ import annotations

import io
from datetime import date

from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Spacer,
    Table,
    TableStyle,
)

from app.services.pdf_billing import (
    BLACK,
    BORDER,
    CYAN,
    GRAY,
    LGRAY,
    NAVY,
    _date,
    _fmt,
    _p,
    build_brand_header,
    build_client_row,
    build_footer_identity,
    build_info_row,
    new_billing_doc,
)


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
    doc, cw, half, gap = new_billing_doc(buf)
    s = []

    # 1. En-tête marque + FACTURE
    s.append(build_brand_header("FACTURE", half, gap))
    s.append(Spacer(1, 4 * mm))

    # 2. Émetteur (gauche) / référence + date (droite)
    ref_info = _p(
        f"<font color='#64748b' size='8'>Référence :</font> <b>{invoice_number}</b><br/>"
        f"<font color='#64748b' size='8'>Date de facturation :</font> {_date(issue_date)}",
        fontSize=8.5,
        fontName="Helvetica",
        textColor=BLACK,
        leading=14,
        alignment=2,
    )
    s.append(build_info_row(ref_info, half, gap))
    s.append(Spacer(1, 6 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=5 * mm))

    # 3. Bloc client
    s.append(build_client_row(client_name, client_email, client_address, half, gap))
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
    s.append(build_footer_identity())
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
