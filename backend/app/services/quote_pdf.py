"""
Generate a professional PDF quote (devis).
French auto-entrepreneur compliant: TVA non applicable, art. 293 B du CGI.
"""
from __future__ import annotations

import io
from datetime import date, timedelta

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

NAVY   = colors.HexColor("#0f172a")
CYAN   = colors.HexColor("#06b6d4")
GRAY   = colors.HexColor("#64748b")
LGRAY  = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#cbd5e1")
WHITE  = colors.white
BLACK  = colors.HexColor("#1e293b")

VENDOR = {
    "name":    "David Rocher",
    "status":  "Entrepreneur individuel",
    "address": "546 Montée Carriat",
    "city":    "01600 Reyrieux, France",
    "siret":   "104 009 634 00015",
    "ape":     "6202A",
    "email":   "contact@cyberscanapp.com",
    "website": "cyberscanapp.com",
}

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


def _p(text: str, **kw) -> Paragraph:
    return Paragraph(text, ParagraphStyle("_", **kw))


def _fmt(cents: int) -> str:
    return f"{cents / 100:,.2f} €".replace(",", " ")


def _date(d: date) -> str:
    m = ["janvier", "février", "mars", "avril", "mai", "juin",
         "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{d.day} {m[d.month - 1]} {d.year}"


def generate_quote_pdf(
    quote_number: str,
    issue_date: date,
    validity_days: int,
    client_name: str,
    client_email: str,
    client_address: str | None,
    subject: str,
    items: list[dict],   # [{description, quantity, unit_price_cents}]
    total_cents: int,
) -> bytes:
    buf = io.BytesIO()
    W, _ = A4
    mg = 16 * mm
    cw = W - 2 * mg
    expiry_date = issue_date + timedelta(days=validity_days)

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=mg, rightMargin=mg,
        topMargin=14 * mm, bottomMargin=16 * mm,
    )
    s = []
    half = cw / 2 - 3 * mm
    gap  = 6 * mm

    # ══════════════════════════════════════════════════════════════════════════
    # 1. HEADER — brand left / DEVIS box right
    # ══════════════════════════════════════════════════════════════════════════
    brand_box = Table([[
        _p("<b>CyberScan</b>",
           fontSize=18, fontName="Helvetica-Bold", textColor=WHITE, leading=22),
        _p("<font color='#06b6d4'>●</font>",
           fontSize=24, fontName="Helvetica-Bold", textColor=CYAN, alignment=2),
    ]], colWidths=[half * 0.7, half * 0.3])
    brand_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))

    devis_box = Table([[
        _p("<b>DEVIS</b>",
           fontSize=20, fontName="Helvetica-Bold", textColor=NAVY, alignment=2),
    ]], colWidths=[half])
    devis_box.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 1, NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))

    top_row = Table([[brand_box, "", devis_box]], colWidths=[half, gap, half])
    top_row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    s.append(top_row)
    s.append(Spacer(1, 4 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 2. INFO ROW — vendor left / ref + dates right
    # ══════════════════════════════════════════════════════════════════════════
    vendor_info = _p(
        f"<b>{VENDOR['name']}</b><br/>"
        f"{VENDOR['status']}<br/>"
        f"{VENDOR['address']}<br/>"
        f"{VENDOR['city']}<br/>"
        f"SIRET : {VENDOR['siret']}<br/>"
        f"APE : {VENDOR['ape']}<br/>"
        f"{VENDOR['email']}",
        fontSize=8.5, fontName="Helvetica", textColor=BLACK, leading=13,
    )

    ref_info = _p(
        f"<font color='#64748b' size='8'>Référence :</font> <b>{quote_number}</b><br/>"
        f"<font color='#64748b' size='8'>Date d'émission :</font> {_date(issue_date)}<br/>"
        f"<font color='#64748b' size='8'>Valable jusqu'au :</font> "
        f"<b>{_date(expiry_date)}</b>"
        f"<font color='#64748b' size='7'> ({validity_days} jours)</font>",
        fontSize=8.5, fontName="Helvetica", textColor=BLACK, leading=14,
        alignment=2,
    )

    info_row = Table([[vendor_info, "", ref_info]], colWidths=[half, gap, half])
    info_row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 5),
    ]))
    s.append(info_row)
    s.append(Spacer(1, 6 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=5 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 3. CLIENT ROW
    # ══════════════════════════════════════════════════════════════════════════
    vendor_label = Table([[
        _p(f"<b>{VENDOR['name']}</b>",
           fontSize=10, fontName="Helvetica-Bold", textColor=NAVY),
    ]], colWidths=[half])
    vendor_label.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))

    addr_lines = f"<b>{client_name}</b><br/>{client_email}"
    if client_address:
        addr_lines += f"<br/>{client_address}"

    client_box = Table([[
        _p(addr_lines,
           fontSize=8.5, fontName="Helvetica", textColor=BLACK, leading=13),
    ]], colWidths=[half])
    client_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LGRAY),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))

    client_row = Table([[vendor_label, "", client_box]], colWidths=[half, gap, half])
    client_row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    s.append(client_row)
    s.append(Spacer(1, 5 * mm))

    # Subject line
    s.append(_p(
        f"<b>Objet :</b> {subject}",
        fontSize=9, fontName="Helvetica", textColor=BLACK,
    ))
    s.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 4. ITEMS TABLE
    # ══════════════════════════════════════════════════════════════════════════
    col_desc = cw * 0.48
    col_qty  = cw * 0.10
    col_up   = cw * 0.21
    col_tot  = cw * 0.21

    header_row = [
        _p("Désignation",     fontSize=8, fontName="Helvetica-Bold", textColor=BLACK),
        _p("Qté",             fontSize=8, fontName="Helvetica-Bold", textColor=BLACK, alignment=1),
        _p("Prix unitaire HT", fontSize=8, fontName="Helvetica-Bold", textColor=BLACK, alignment=2),
        _p("Total HT",        fontSize=8, fontName="Helvetica-Bold", textColor=BLACK, alignment=2),
    ]

    table_rows = [header_row]
    for item in items:
        qty        = item.get("quantity", 1)
        up_cents   = item.get("unit_price_cents", 0)
        line_total = qty * up_cents
        table_rows.append([
            _p(item.get("description", ""), fontSize=8.5, fontName="Helvetica",
               textColor=BLACK, leading=12),
            _p(str(qty), fontSize=8.5, fontName="Helvetica", textColor=BLACK, alignment=1),
            _p(_fmt(up_cents),   fontSize=8.5, fontName="Helvetica", textColor=BLACK, alignment=2),
            _p(_fmt(line_total), fontSize=8.5, fontName="Helvetica", textColor=BLACK, alignment=2),
        ])

    items_style = [
        ("BACKGROUND",    (0, 0), (-1, 0),  LGRAY),
        ("LINEBELOW",     (0, 0), (-1, 0),  1, NAVY),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.4, BORDER),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
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

    totals_box = Table([
        [_p("Total HT",          fontSize=9,   fontName="Helvetica-Bold",    textColor=NAVY),
         _p(f"<b>{_fmt(total_cents)}</b>", fontSize=10, fontName="Helvetica-Bold",
            textColor=NAVY, alignment=2)],
        [_p("TVA non applicable", fontSize=7.5, fontName="Helvetica-Oblique", textColor=GRAY),
         _p("art. 293 B du CGI",  fontSize=7.5, fontName="Helvetica-Oblique",
            textColor=GRAY, alignment=2)],
        [_p("Net à payer",        fontSize=9,   fontName="Helvetica-Bold",    textColor=NAVY),
         _p(f"<b>{_fmt(total_cents)}</b>", fontSize=10, fontName="Helvetica-Bold",
            textColor=NAVY, alignment=2)],
    ], colWidths=[tot_w * 0.55, tot_w * 0.45])
    totals_box.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEABOVE",     (0, 0), (-1, 0),  2,   CYAN),
        ("LINEABOVE",     (0, 2), (-1, 2),  0.5, BORDER),
        ("BACKGROUND",    (0, 0), (-1, 0),  LGRAY),
        ("BACKGROUND",    (0, 2), (-1, 2),  LGRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))

    total_row = Table([[_p(""), totals_box]], colWidths=[spacer_w, tot_w])
    total_row.setStyle(TableStyle([
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
    ]))
    s.append(total_row)
    s.append(Spacer(1, 6 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 6. BON POUR ACCORD + SIGNATURE
    # ══════════════════════════════════════════════════════════════════════════
    validity_box = Table([[
        _p(
            f"<font color='#64748b' size='7.5'>Devis valable jusqu'au :</font> "
            f"<b>{_date(expiry_date)}</b>",
            fontSize=8.5, fontName="Helvetica", textColor=BLACK,
        ),
    ]], colWidths=[half])
    validity_box.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))

    bpa_box = Table([
        [_p("<b>Bon pour accord</b>",
            fontSize=8.5, fontName="Helvetica-Bold", textColor=NAVY)],
        [_p(f"<font color='#64748b' size='7.5'>Fait à ____________, le ____________</font>",
            fontSize=8, fontName="Helvetica", textColor=GRAY)],
        [_p("<font color='#64748b' size='7'>Nom, prénom et signature du client :</font>",
            fontSize=7.5, fontName="Helvetica", textColor=GRAY)],
        [_p("", fontSize=8)],
    ], colWidths=[half])
    bpa_box.setStyle(TableStyle([
        ("BOX",           (0, 0), (-1, -1), 1, NAVY),
        ("LINEABOVE",     (0, 0), (-1, 0),  2, CYAN),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (0, 0),   8),
        ("BOTTOMPADDING", (0, 0), (0, 0),   4),
        ("TOPPADDING",    (0, 1), (0, 1),   4),
        ("BOTTOMPADDING", (0, 1), (0, 1),   2),
        ("TOPPADDING",    (0, 2), (0, 2),   4),
        ("BOTTOMPADDING", (0, 2), (0, 2),   0),
        ("TOPPADDING",    (0, 3), (0, 3),   30),
        ("BOTTOMPADDING", (0, 3), (0, 3),   8),
    ]))

    bpa_row = Table([[validity_box, "", bpa_box]], colWidths=[half, gap, half])
    bpa_row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    s.append(bpa_row)
    s.append(Spacer(1, 8 * mm))

    # ══════════════════════════════════════════════════════════════════════════
    # 7. FOOTER — CGV + legal
    # ══════════════════════════════════════════════════════════════════════════
    s.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    s.append(_p(
        f"{VENDOR['name']} — SIRET {VENDOR['siret']} — APE {VENDOR['ape']} — "
        f"{VENDOR['email']} — {VENDOR['website']}",
        fontSize=7, fontName="Helvetica", textColor=GRAY, alignment=1, leading=10,
    ))
    s.append(_p(
        CGV,
        fontSize=6.5, fontName="Helvetica", textColor=GRAY, alignment=1,
        leading=9, spaceBefore=3,
    ))

    doc.build(s)
    return buf.getvalue()
