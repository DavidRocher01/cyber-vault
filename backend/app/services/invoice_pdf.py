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
NAVY      = colors.HexColor("#0f172a")
NAVY_MID  = colors.HexColor("#1e293b")
CYAN      = colors.HexColor("#06b6d4")
CYAN_DARK = colors.HexColor("#0891b2")
LIGHT     = colors.HexColor("#f8fafc")
LIGHT2    = colors.HexColor("#f1f5f9")
MID       = colors.HexColor("#64748b")
DARK      = colors.HexColor("#1e293b")
WHITE     = colors.white
BORDER    = colors.HexColor("#e2e8f0")
GREEN     = colors.HexColor("#10b981")

# ── Vendor ────────────────────────────────────────────────────────────────────
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


def _p(text: str, **kw) -> Paragraph:
    style = ParagraphStyle("_", **kw)
    return Paragraph(text, style)


def _fmt_amount(cents: int) -> str:
    euros = cents / 100
    return f"{euros:,.2f} €".replace(",", " ")


def _fmt_date(d: date) -> str:
    MONTHS = ["janvier","février","mars","avril","mai","juin",
              "juillet","août","septembre","octobre","novembre","décembre"]
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


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
    W, H = A4
    margin = 16 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0,
        bottomMargin=16 * mm,
    )

    cw = W - 2 * margin
    story = []

    # ── Hero header (dark band) ───────────────────────────────────────────────
    hero = Table([[
        # Left: brand
        _p(f"<b>{VENDOR['name']}</b>",
           fontSize=14, fontName="Helvetica-Bold", textColor=WHITE, leading=18),
        # Right: FACTURE label
        _p("<b>FACTURE</b>",
           fontSize=28, fontName="Helvetica-Bold", textColor=CYAN,
           alignment=2),
    ]], colWidths=[cw * 0.6, cw * 0.4])
    hero.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(hero)

    # Sub-header: vendor details left, invoice number right
    sub = Table([[
        _p(f"{VENDOR['status']}  ·  {VENDOR['address']}, {VENDOR['city']}<br/>"
           f"SIRET {VENDOR['siret']}  ·  APE {VENDOR['ape']}  ·  {VENDOR['email']}",
           fontSize=7.5, fontName="Helvetica", textColor=colors.HexColor("#94a3b8"),
           leading=12),
        _p(f"N° <b>{invoice_number}</b>",
           fontSize=9, fontName="Helvetica", textColor=colors.HexColor("#94a3b8"),
           alignment=2),
    ]], colWidths=[cw * 0.65, cw * 0.35])
    sub.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NAVY_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(sub)

    # Cyan accent line
    story.append(HRFlowable(width=cw, thickness=2.5, color=CYAN, spaceAfter=7 * mm, spaceBefore=0))

    # ── Meta + client (two columns) ──────────────────────────────────────────
    # Build client address lines
    client_lines = f"<b>{client_name}</b><br/>{client_email}"
    if client_address:
        client_lines += f"<br/>{client_address}"

    client_block = Table(
        [[_p(f"<b>Facturé à</b><br/>{client_lines}",
             fontSize=9, fontName="Helvetica", textColor=DARK, leading=14)]],
        colWidths=[cw * 0.42],
    )
    client_block.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LINEABOVE",     (0, 0), (-1, 0), 2.5, CYAN),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))

    date_block = Table(
        [[
            _p("Date d'émission", fontSize=7.5, fontName="Helvetica",
               textColor=MID, alignment=2),
        ], [
            _p(f"<b>{_fmt_date(issue_date)}</b>", fontSize=10,
               fontName="Helvetica-Bold", textColor=DARK, alignment=2),
        ], [
            _p("Statut", fontSize=7.5, fontName="Helvetica",
               textColor=MID, alignment=2, spaceBefore=8),
        ], [
            _p("<b>● Payée</b>", fontSize=9, fontName="Helvetica-Bold",
               textColor=GREEN, alignment=2),
        ]],
        colWidths=[cw * 0.38],
    )
    date_block.setStyle(TableStyle([
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))

    meta_row = Table(
        [[client_block, Spacer(1, 1), date_block]],
        colWidths=[cw * 0.42, cw * 0.15, cw * 0.43],
    )
    meta_row.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 0),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(meta_row)
    story.append(Spacer(1, 8 * mm))

    # ── Items table ──────────────────────────────────────────────────────────
    col_desc = cw * 0.70
    col_amt  = cw * 0.30

    items_table = Table(
        [
            # Header row
            [
                _p("Description", fontSize=8.5, fontName="Helvetica-Bold",
                   textColor=WHITE),
                _p("Montant TTC", fontSize=8.5, fontName="Helvetica-Bold",
                   textColor=WHITE, alignment=2),
            ],
            # Data row
            [
                _p(description, fontSize=9, fontName="Helvetica", textColor=DARK, leading=13),
                _p(_fmt_amount(amount_cents), fontSize=9, fontName="Helvetica",
                   textColor=DARK, alignment=2),
            ],
        ],
        colWidths=[col_desc, col_amt],
    )
    items_table.setStyle(TableStyle([
        # Header
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("TOPPADDING",    (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 9),
        ("LEFTPADDING",   (0, 0), (-1, 0), 12),
        ("RIGHTPADDING",  (0, 0), (-1, 0), 12),
        # Data rows
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("TOPPADDING",    (0, 1), (-1, -1), 11),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 11),
        ("LEFTPADDING",   (0, 1), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 1), (-1, -1), 12),
        # Borders
        ("LINEBELOW",     (0, 0), (-1, 0), 2, CYAN),
        ("LINEBELOW",     (0, 1), (-1, -1), 0.5, BORDER),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(items_table)

    # ── Total row ─────────────────────────────────────────────────────────────
    total_table = Table(
        [["", _p("Total TTC", fontSize=10, fontName="Helvetica-Bold",
                 textColor=NAVY, alignment=2),
              _p(f"<b>{_fmt_amount(amount_cents)}</b>", fontSize=11,
                 fontName="Helvetica-Bold", textColor=NAVY, alignment=2)]],
        colWidths=[col_desc * 0.55, col_desc * 0.45, col_amt],
    )
    total_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT2),
        ("TOPPADDING",    (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("LINEABOVE",     (0, 0), (-1, 0), 2, CYAN),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(total_table)
    story.append(Spacer(1, 5 * mm))

    # ── TVA notice ────────────────────────────────────────────────────────────
    story.append(_p(
        "TVA non applicable, art. 293 B du CGI",
        fontSize=7.5, fontName="Helvetica-Oblique", textColor=MID,
    ))
    story.append(Spacer(1, 12 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=cw, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    story.append(_p(
        f"{VENDOR['name']} — SIRET {VENDOR['siret']} — {VENDOR['email']} — {VENDOR['website']}",
        fontSize=7, fontName="Helvetica", textColor=MID, alignment=1,
    ))

    doc.build(story)
    return buf.getvalue()
