"""
Generate a professional PDF invoice (clean white style, not the cyberscan dark theme).
Compliant with French auto-entrepreneur rules: TVA non applicable, art. 293 B du CGI.
"""
from __future__ import annotations

import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
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
NAVY    = colors.HexColor("#1e3a5f")
ACCENT  = colors.HexColor("#2563eb")
LIGHT   = colors.HexColor("#f1f5f9")
MID     = colors.HexColor("#64748b")
BLACK   = colors.HexColor("#0f172a")
WHITE   = colors.white
BORDER  = colors.HexColor("#cbd5e1")

# ── Vendor info (David Rocher — Entrepreneur individuel) ───────────────────────
VENDOR = {
    "name":    "David Rocher",
    "status":  "Entrepreneur individuel",
    "address": "546 Montée Carriat",
    "city":    "01600 Reyrieux, France",
    "siret":   "104 009 634 00015",
    "ape":     "6202A — Conseil en systèmes et logiciels informatiques",
    "email":   "contact@cyberscanapp.com",
    "website": "cyberscanapp.com",
}


def _styles() -> dict:
    base = getSampleStyleSheet()

    def s(name, **kw) -> ParagraphStyle:
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "title":   s("InvTitle",   fontSize=22, fontName="Helvetica-Bold",  textColor=NAVY,   spaceAfter=2),
        "number":  s("InvNum",     fontSize=11, fontName="Helvetica",       textColor=MID,    spaceAfter=8),
        "h2":      s("InvH2",      fontSize=10, fontName="Helvetica-Bold",  textColor=NAVY,   spaceAfter=3),
        "body":    s("InvBody",    fontSize=9,  fontName="Helvetica",       textColor=BLACK,  leading=13),
        "small":   s("InvSmall",   fontSize=7,  fontName="Helvetica",       textColor=MID,    leading=10),
        "bold":    s("InvBold",    fontSize=9,  fontName="Helvetica-Bold",  textColor=BLACK),
        "total":   s("InvTotal",   fontSize=11, fontName="Helvetica-Bold",  textColor=NAVY),
        "tva":     s("InvTva",     fontSize=8,  fontName="Helvetica-Oblique", textColor=MID,  leading=11),
        "footer":  s("InvFooter",  fontSize=7,  fontName="Helvetica",       textColor=MID,    leading=10, alignment=1),
    }


def _fmt_amount(cents: int) -> str:
    euros = cents / 100
    return f"{euros:,.2f} €".replace(",", " ")


def _fmt_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


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
    margin = 18 * mm

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=14 * mm,
        bottomMargin=20 * mm,
    )

    content_w = W - 2 * margin
    st = _styles()
    story = []

    # ── Header band ────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"<b>{VENDOR['name']}</b><br/>"
                  f"{VENDOR['status']}<br/>"
                  f"{VENDOR['address']}<br/>"
                  f"{VENDOR['city']}<br/>"
                  f"SIRET : {VENDOR['siret']}<br/>"
                  f"APE : {VENDOR['ape']}<br/>"
                  f"{VENDOR['email']}",
                  st["body"]),
        Paragraph(f"<b>FACTURE</b>", ParagraphStyle(
            "BigFact", fontSize=26, fontName="Helvetica-Bold",
            textColor=NAVY, alignment=2,
        )),
    ]]
    header_table = Table(header_data, colWidths=[content_w * 0.55, content_w * 0.45])
    header_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=content_w, thickness=1.5, color=ACCENT, spaceAfter=4 * mm))

    # ── Invoice meta ───────────────────────────────────────────────────────────
    meta_data = [[
        Paragraph(f"N° {invoice_number}", st["title"]),
        Paragraph(f"Date d'émission : <b>{_fmt_date(issue_date)}</b>", st["body"]),
    ]]
    meta_table = Table(meta_data, colWidths=[content_w * 0.6, content_w * 0.4])
    meta_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("ALIGN",        (1, 0), (1, 0), "RIGHT"),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # ── Client block ───────────────────────────────────────────────────────────
    client_lines = f"<b>Facturé à</b><br/>{client_name}<br/>{client_email}"
    if client_address:
        client_lines += f"<br/>{client_address}"

    client_block = Table(
        [[Paragraph(client_lines, st["body"])]],
        colWidths=[content_w * 0.45],
    )
    client_block.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROUNDEDCORNERS", [4]),
        ("BOX",           (0, 0), (-1, -1), 0.5, BORDER),
    ]))
    story.append(client_block)
    story.append(Spacer(1, 8 * mm))

    # ── Line items table ───────────────────────────────────────────────────────
    items_header = [
        Paragraph("Description", st["bold"]),
        Paragraph("Montant HT", ParagraphStyle(
            "RBold", fontSize=9, fontName="Helvetica-Bold",
            textColor=BLACK, alignment=2,
        )),
    ]
    items_row = [
        Paragraph(description, st["body"]),
        Paragraph(_fmt_amount(amount_cents), ParagraphStyle(
            "RBody", fontSize=9, fontName="Helvetica", textColor=BLACK, alignment=2,
        )),
    ]

    items_table = Table(
        [items_header, items_row],
        colWidths=[content_w * 0.72, content_w * 0.28],
    )
    items_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("BACKGROUND",    (0, 1), (-1, -1), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.4, BORDER),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 4 * mm))

    # ── Total block ────────────────────────────────────────────────────────────
    total_data = [
        ["Total HT", _fmt_amount(amount_cents)],
        ["TVA",      "Non applicable"],
        ["Total TTC", _fmt_amount(amount_cents)],
    ]
    total_styles_list = [
        ("FONTNAME",      (0, 0), (-1, 1), "Helvetica"),
        ("FONTNAME",      (0, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("ALIGN",         (0, 0), (-1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TEXTCOLOR",     (0, 0), (-1, 1), MID),
        ("TEXTCOLOR",     (0, 2), (-1, 2), NAVY),
        ("FONTSIZE",      (0, 2), (-1, 2), 11),
        ("BACKGROUND",    (0, 2), (-1, 2), LIGHT),
        ("LINEABOVE",     (0, 2), (-1, 2), 1, ACCENT),
    ]
    total_table = Table(total_data, colWidths=[content_w * 0.72, content_w * 0.28])
    total_table.setStyle(TableStyle(total_styles_list))
    story.append(total_table)
    story.append(Spacer(1, 4 * mm))

    # ── TVA notice ─────────────────────────────────────────────────────────────
    story.append(Paragraph(
        "TVA non applicable, art. 293 B du CGI",
        st["tva"],
    ))
    story.append(Spacer(1, 10 * mm))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(HRFlowable(width=content_w, thickness=0.5, color=BORDER, spaceAfter=3 * mm))
    story.append(Paragraph(
        f"{VENDOR['name']} — SIRET {VENDOR['siret']} — {VENDOR['email']} — {VENDOR['website']}",
        st["footer"],
    ))

    doc.build(story)
    return buf.getvalue()
