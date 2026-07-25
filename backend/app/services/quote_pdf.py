"""
Generate a professional PDF quote (devis).
French auto-entrepreneur compliant: TVA non applicable, art. 293 B du CGI.
"""

from __future__ import annotations

import io
from datetime import date, timedelta

from reportlab.lib import colors
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

CGV = (
    "Conditions générales de vente — "
    "Le présent devis est valable pour la durée indiquée ci-dessus. "
    "Tout accord du client doit être formalisé par écrit (email ou signature). "
    "Acompte de 30 % à la commande, solde à la livraison. "
    "En cas d'annulation après acceptation, l'acompte reste acquis. "
    "Tous les travaux réalisés restent la propriété du prestataire jusqu'au paiement intégral. "
    "Les informations communiquées dans le cadre de cette mission sont traitées de façon confidentielle. "
    "TVA non applicable, art. 293 B du CGI. "
    "En cas de retard de paiement : indemnité forfaitaire de recouvrement de 40 € (art. L.441-10 C. com.)."
)


def generate_quote_pdf(
    quote_number: str,
    issue_date: date,
    validity_days: int,
    client_name: str,
    client_email: str,
    client_address: str | None,
    subject: str,
    items: list[dict],  # [{description, quantity, unit_price_cents}]
    total_cents: int,
) -> bytes:
    buf = io.BytesIO()
    doc, cw, half, gap = new_billing_doc(buf)
    expiry_date = issue_date + timedelta(days=validity_days)
    s = []

    # 1. En-tête marque + DEVIS
    s.append(build_brand_header("DEVIS", half, gap))
    s.append(Spacer(1, 4 * mm))

    # 2. Émetteur (gauche) / référence + dates (droite)
    ref_info = _p(
        f"<font color='#64748b' size='8'>Référence :</font> <b>{quote_number}</b><br/>"
        f"<font color='#64748b' size='8'>Date d'émission :</font> {_date(issue_date)}<br/>"
        f"<font color='#64748b' size='8'>Valable jusqu'au :</font> "
        f"<b>{_date(expiry_date)}</b>"
        f"<font color='#64748b' size='7'> ({validity_days} jours)</font>",
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
    s.append(Spacer(1, 5 * mm))

    # Subject line
    s.append(
        _p(
            f"<b>Objet :</b> {subject}",
            fontSize=9,
            fontName="Helvetica",
            textColor=BLACK,
        )
    )
    s.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 4. ITEMS TABLE
    # ══════════════════════════════════════════════════════════════════════════
    col_desc = cw * 0.48
    col_qty = cw * 0.10
    col_up = cw * 0.21
    col_tot = cw * 0.21

    header_row = [
        _p("Désignation", fontSize=8, fontName="Helvetica-Bold", textColor=BLACK),
        _p("Qté", fontSize=8, fontName="Helvetica-Bold", textColor=BLACK, alignment=1),
        _p(
            "Prix unitaire HT",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=BLACK,
            alignment=2,
        ),
        _p(
            "Total HT",
            fontSize=8,
            fontName="Helvetica-Bold",
            textColor=BLACK,
            alignment=2,
        ),
    ]

    table_rows = [header_row]
    for item in items:
        qty = item.get("quantity", 1)
        up_cents = item.get("unit_price_cents", 0)
        line_total = qty * up_cents
        table_rows.append(
            [
                _p(
                    item.get("description", ""),
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                    leading=12,
                ),
                _p(
                    str(qty),
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                    alignment=1,
                ),
                _p(
                    _fmt(up_cents),
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                    alignment=2,
                ),
                _p(
                    _fmt(line_total),
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                    alignment=2,
                ),
            ]
        )

    items_style = [
        ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
        ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, BORDER),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(table_rows)):
        if i % 2 == 0:
            items_style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8fafc")))

    items_tbl = Table(table_rows, colWidths=[col_desc, col_qty, col_up, col_tot])
    items_tbl.setStyle(TableStyle(items_style))
    s.append(items_tbl)
    s.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 5. TOTAL BLOCK (right-aligned)
    # ══════════════════════════════════════════════════════════════════════════
    tot_w = cw * 0.42
    spacer_w = cw - tot_w

    totals_box = Table(
        [
            [
                _p("Total HT", fontSize=9, fontName="Helvetica-Bold", textColor=NAVY),
                _p(
                    f"<b>{_fmt(total_cents)}</b>",
                    fontSize=10,
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
                _p("Net à payer", fontSize=9, fontName="Helvetica-Bold", textColor=NAVY),
                _p(
                    f"<b>{_fmt(total_cents)}</b>",
                    fontSize=10,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                    alignment=2,
                ),
            ],
        ],
        colWidths=[tot_w * 0.55, tot_w * 0.45],
    )
    totals_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LINEABOVE", (0, 0), (-1, 0), 2, CYAN),
                ("LINEABOVE", (0, 2), (-1, 2), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), LGRAY),
                ("BACKGROUND", (0, 2), (-1, 2), LGRAY),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )

    total_row = Table([[_p(""), totals_box]], colWidths=[spacer_w, tot_w])
    total_row.setStyle(
        TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    s.append(total_row)
    s.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 6. BON POUR ACCORD + SIGNATURE
    # ══════════════════════════════════════════════════════════════════════════
    validity_box = Table(
        [
            [
                _p(
                    f"<font color='#64748b' size='7.5'>Devis valable jusqu'au :</font> "
                    f"<b>{_date(expiry_date)}</b>",
                    fontSize=8.5,
                    fontName="Helvetica",
                    textColor=BLACK,
                ),
            ]
        ],
        colWidths=[half],
    )
    validity_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )

    bpa_box = Table(
        [
            [
                _p(
                    "<b>Bon pour accord</b>",
                    fontSize=8.5,
                    fontName="Helvetica-Bold",
                    textColor=NAVY,
                )
            ],
            [
                _p(
                    "<font color='#64748b' size='7.5'>Fait à ____________, le ____________</font>",
                    fontSize=8,
                    fontName="Helvetica",
                    textColor=GRAY,
                )
            ],
            [
                _p(
                    "<font color='#64748b' size='7'>Nom, prénom et signature du client :</font>",
                    fontSize=7.5,
                    fontName="Helvetica",
                    textColor=GRAY,
                )
            ],
            [_p("", fontSize=8)],
        ],
        colWidths=[half],
    )
    bpa_box.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1, NAVY),
                ("LINEABOVE", (0, 0), (-1, 0), 2, CYAN),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (0, 0), 8),
                ("BOTTOMPADDING", (0, 0), (0, 0), 4),
                ("TOPPADDING", (0, 1), (0, 1), 4),
                ("BOTTOMPADDING", (0, 1), (0, 1), 2),
                ("TOPPADDING", (0, 2), (0, 2), 4),
                ("BOTTOMPADDING", (0, 2), (0, 2), 0),
                ("TOPPADDING", (0, 3), (0, 3), 30),
                ("BOTTOMPADDING", (0, 3), (0, 3), 8),
            ]
        )
    )

    bpa_row = Table([[validity_box, "", bpa_box]], colWidths=[half, gap, half])
    bpa_row.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    s.append(bpa_row)
    s.append(Spacer(1, 8 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 7. FOOTER — CGV + legal
    # ══════════════════════════════════════════════════════════════════════════
    s.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    s.append(build_footer_identity())
    s.append(
        _p(
            CGV,
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
