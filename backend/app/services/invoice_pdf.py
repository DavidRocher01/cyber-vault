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
NAVY   = colors.HexColor("#0f172a")
CYAN   = colors.HexColor("#06b6d4")
GRAY   = colors.HexColor("#64748b")
LGRAY  = colors.HexColor("#f1f5f9")
BORDER = colors.HexColor("#e2e8f0")
GREEN  = colors.HexColor("#059669")
WHITE  = colors.white

# ── Vendor ────────────────────────────────────────────────────────────────────
VENDOR = {
    "name":    "David Rocher",
    "status":  "Entrepreneur individuel",
    "address": "546 Montée Carriat, 01600 Reyrieux, France",
    "siret":   "104 009 634 00015",
    "ape":     "6202A",
    "email":   "contact@cyberscanapp.com",
    "website": "cyberscanapp.com",
}


def _p(text: str, **kw) -> Paragraph:
    return Paragraph(text, ParagraphStyle("_", **kw))


def _fmt(cents: int) -> str:
    return f"{cents / 100:,.2f} €".replace(",", " ")


def _date(d: date) -> str:
    m = ["janvier","février","mars","avril","mai","juin",
         "juillet","août","septembre","octobre","novembre","décembre"]
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
    mg = 18 * mm
    cw = W - 2 * mg

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=mg, rightMargin=mg,
        topMargin=16 * mm, bottomMargin=18 * mm,
    )
    s = []

    # ── Top accent strip ──────────────────────────────────────────────────────
    strip = Table([[""]], colWidths=[cw])
    strip.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CYAN),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    s.append(strip)
    s.append(Spacer(1, 6 * mm))

    # ── Header: company left — FACTURE box right ──────────────────────────────
    facture_box = Table(
        [[_p("FACTURE", fontSize=18, fontName="Helvetica-Bold",
             textColor=WHITE, alignment=1)]],
        colWidths=[46 * mm],
    )
    facture_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
    ]))

    header = Table([[
        _p(f"<b>{VENDOR['name']}</b><br/>"
           f"<font color='#64748b' size='8'>{VENDOR['status']}</font>",
           fontSize=13, fontName="Helvetica-Bold", textColor=NAVY, leading=18),
        facture_box,
    ]], colWidths=[cw - 50 * mm, 50 * mm])
    header.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
    ]))
    s.append(header)
    s.append(Spacer(1, 3 * mm))

    # Sub-line: vendor details
    s.append(_p(
        f"{VENDOR['address']}  ·  SIRET {VENDOR['siret']}  "
        f"·  APE {VENDOR['ape']}  ·  {VENDOR['email']}",
        fontSize=7.5, fontName="Helvetica", textColor=GRAY, leading=11,
    ))
    s.append(Spacer(1, 5 * mm))
    s.append(HRFlowable(width=cw, thickness=0.6, color=BORDER, spaceAfter=6 * mm))

    # ── Invoice number + date ─────────────────────────────────────────────────
    meta = Table([[
        _p(f"N° <b>{invoice_number}</b>",
           fontSize=10, fontName="Helvetica", textColor=NAVY),
        _p(f"<font color='#64748b' size='8'>Date d'émission</font><br/>"
           f"<b>{_date(issue_date)}</b>",
           fontSize=9, fontName="Helvetica", textColor=NAVY,
           alignment=2, leading=13),
    ]], colWidths=[cw * 0.5, cw * 0.5])
    meta.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    s.append(meta)
    s.append(Spacer(1, 6 * mm))

    # ── Client block ──────────────────────────────────────────────────────────
    addr_lines = f"<b>{client_name}</b><br/>{client_email}"
    if client_address:
        addr_lines += f"<br/><font color='#64748b'>{client_address}</font>"

    client_tbl = Table(
        [[_p(addr_lines, fontSize=9, fontName="Helvetica", textColor=NAVY, leading=14)]],
        colWidths=[cw * 0.44],
    )
    client_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LGRAY),
        ("LEFTPADDING",   (0, 0), (-1, -1), 11),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 11),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LINEBEFORE",    (0, 0), (0, -1), 3, CYAN),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))

    status_tbl = Table([[
        _p("● Payée",
           fontSize=9, fontName="Helvetica-Bold", textColor=GREEN, alignment=2),
    ]], colWidths=[cw * 0.44])
    status_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor("#f0fdf4")),
        ("LEFTPADDING",   (0, 0), (-1, -1), 11),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 11),
        ("TOPPADDING",    (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("BOX",           (0, 0), (-1, -1), 0.5, colors.HexColor("#bbf7d0")),
    ]))

    row = Table([[client_tbl, "", status_tbl]],
                colWidths=[cw * 0.44, cw * 0.12, cw * 0.44])
    row.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    s.append(row)
    s.append(Spacer(1, 8 * mm))

    # ── Items table ───────────────────────────────────────────────────────────
    col_d, col_a = cw * 0.70, cw * 0.30

    tbl = Table([
        [
            _p("Description", fontSize=8.5, fontName="Helvetica-Bold", textColor=WHITE),
            _p("Montant TTC", fontSize=8.5, fontName="Helvetica-Bold",
               textColor=WHITE, alignment=2),
        ],
        [
            _p(description, fontSize=9, fontName="Helvetica", textColor=NAVY, leading=13),
            _p(_fmt(amount_cents), fontSize=9, fontName="Helvetica",
               textColor=NAVY, alignment=2),
        ],
    ], colWidths=[col_d, col_a])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  NAVY),
        ("TOPPADDING",    (0, 0), (-1, 0),  9),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  9),
        ("LEFTPADDING",   (0, 0), (-1, 0),  12),
        ("RIGHTPADDING",  (0, 0), (-1, 0),  12),
        ("LINEBELOW",     (0, 0), (-1, 0),  2.5, CYAN),
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("TOPPADDING",    (0, 1), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 12),
        ("LEFTPADDING",   (0, 1), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 1), (-1, -1), 12),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.4, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    s.append(tbl)

    # ── Total ─────────────────────────────────────────────────────────────────
    tot = Table([[
        _p("Total TTC", fontSize=10, fontName="Helvetica-Bold",
           textColor=NAVY, alignment=2),
        _p(f"<b>{_fmt(amount_cents)}</b>", fontSize=11, fontName="Helvetica-Bold",
           textColor=NAVY, alignment=2),
    ]], colWidths=[col_d, col_a])
    tot.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LGRAY),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("LINEABOVE",     (0, 0), (-1, 0),  1.5, CYAN),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    s.append(tot)
    s.append(Spacer(1, 5 * mm))

    # ── TVA notice ────────────────────────────────────────────────────────────
    s.append(_p(
        "TVA non applicable, art. 293 B du CGI",
        fontSize=7.5, fontName="Helvetica-Oblique", textColor=GRAY,
    ))
    s.append(Spacer(1, 14 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    s.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    s.append(_p(
        f"{VENDOR['name']} — SIRET {VENDOR['siret']} — "
        f"{VENDOR['email']} — {VENDOR['website']}",
        fontSize=7, fontName="Helvetica", textColor=GRAY, alignment=1,
    ))

    doc.build(s)
    return buf.getvalue()
