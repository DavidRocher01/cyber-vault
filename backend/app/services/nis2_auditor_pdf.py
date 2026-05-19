"""
nis2_auditor_pdf.py — "Prêt-à-déposer" NIS2 document for certified auditor review.

Produces a formal PDF structured for regulatory submission:
  1. Cover — attestation, entity info, score
  2. Table of contents (static)
  3. Compliance summary by domain
  4. Detailed findings per category (conformant / partial / non-conformant)
  5. Action plan — non-conformant items with priority
  6. Auditor declaration block (signature placeholder)
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

from app.services.pdf_brand import (
    DARK_BG, CARD_BG, BORDER, CYAN, GREEN, YELLOW, RED, GRAY, WHITE,
    PAGE_W, PAGE_H, MARGIN, FOOTER_H,
    score_color, get_styles, section_rule, draw_compliance_cover,
    STATUS_COLOR, STATUS_LABEL,
)

_PRIORITY = {"non_compliant": "HAUTE", "partial": "MOYENNE", "compliant": "—", "na": "—"}
_PRIORITY_COL = {"HAUTE": RED, "MOYENNE": YELLOW, "—": GRAY}


def _draw_auditor_page(canvas, doc, *, user_email: str, date_str: str) -> None:
    acc = colors.HexColor("#8b5cf6")
    M = MARGIN * mm
    BAND_H = 14 * mm
    band_y = PAGE_H - BAND_H
    band_cy = PAGE_H - BAND_H / 2
    today = date_str[:10]

    canvas.saveState()

    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    canvas.setFillColor(colors.HexColor("#0f0a28"))
    canvas.rect(0, band_y, PAGE_W, BAND_H, fill=1, stroke=0)
    canvas.setFillColor(acc)
    canvas.rect(0, band_y, 2 * mm, BAND_H, fill=1, stroke=0)
    canvas.setStrokeColor(acc)
    canvas.setLineWidth(2.5)
    canvas.line(0, band_y, PAGE_W, band_y)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", BAND_H * 0.55)
    canvas.drawString(M + 3 * mm, band_cy - BAND_H * 0.12, "CyberScan")
    canvas.setFillColor(acc)
    canvas.setFont("Helvetica-Bold", BAND_H * 0.45)
    canvas.drawRightString(PAGE_W - M, band_cy + BAND_H * 0.10, "NIS2 — DOCUMENT OFFICIEL")
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", BAND_H * 0.35)
    canvas.drawRightString(PAGE_W - M, band_cy - BAND_H * 0.28, today)

    fy = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, fy, PAGE_W - M, fy)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, fy - 5 * mm, f"Document confidentiel — {user_email}")
    canvas.drawCentredString(PAGE_W / 2, fy - 5 * mm, f"Page {doc.page}")
    canvas.drawRightString(PAGE_W - M, fy - 5 * mm, today)

    canvas.restoreState()


def _domain_scores(categories: list, items: dict) -> list[tuple[str, int]]:
    result = []
    for cat in categories:
        cat_items = cat["items"]
        scorable = [i for i in cat_items if items.get(i["id"], "non_compliant") != "na"]
        if not scorable:
            result.append((cat.get("label", cat.get("name", "")), 0))
            continue
        pts = sum(
            2 if items.get(i["id"], "non_compliant") == "compliant"
            else 1 if items.get(i["id"], "non_compliant") == "partial" else 0
            for i in scorable
        )
        pct = round(pts / (len(scorable) * 2) * 100)
        result.append((cat.get("label", cat.get("name", "")), pct))
    return result


def generate_nis2_auditor_pdf(
    *,
    categories: list[dict[str, Any]],
    items: dict[str, str],
    score: int,
    user_email: str,
    updated_at: datetime | None,
    company_name: str = "",
) -> bytes:
    date_str = (updated_at or datetime.now()).strftime("%d/%m/%Y à %Hh%M")
    today_str = datetime.now().strftime("%d/%m/%Y")
    domain_scores = _domain_scores(categories, items)

    total = sum(1 for _ in (item for cat in categories for item in cat["items"]))
    compliant = sum(1 for cat in categories for item in cat["items"]
                    if items.get(item["id"]) == "compliant")
    partial = sum(1 for cat in categories for item in cat["items"]
                  if items.get(item["id"]) == "partial")
    nc = sum(1 for cat in categories for item in cat["items"]
             if items.get(item["id"]) == "non_compliant")
    na = sum(1 for cat in categories for item in cat["items"]
             if items.get(item["id"]) == "na")
    score_label = "Conforme" if score >= 80 else "Partiel" if score >= 50 else "Non conforme"

    buf = io.BytesIO()
    M = MARGIN * mm
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M,
        topMargin=(14 + 4) * mm,
        bottomMargin=(FOOTER_H + 6) * mm,
    )

    cover_kwargs = dict(
        doc_type="nis2",
        title_line1="Document NIS2 Prêt-à-Déposer",
        title_line2=company_name or user_email,
        score=score,
        score_label=score_label,
        total=total,
        compliant=compliant,
        partial=partial,
        nc=nc,
        na=na,
        date_str=date_str,
        domain_scores=domain_scores,
    )

    def on_cover(c, d):
        draw_compliance_cover(c, d, **cover_kwargs)

    def on_page(c, d):
        _draw_auditor_page(c, d, user_email=user_email, date_str=date_str)

    styles = get_styles("nis2")
    story: list = [PageBreak()]

    # ── 1. Attestation block ───────────────────────────────────────────────
    story.append(Paragraph("1. Attestation de conformité", styles["section"]))
    story.append(section_rule(doc.width, "nis2"))
    story.append(Spacer(1, 3 * mm))

    attest_data = [
        ["Entité", company_name or "—"],
        ["Responsable", user_email],
        ["Date d'évaluation", date_str],
        ["Score de conformité", f"{score} %"],
        ["Périmètre", "Directive NIS2 — Mesures de cybersécurité (Art. 21)"],
        ["Outil d'évaluation", "CyberScan — cyberscanapp.com"],
    ]
    attest_tbl = Table(attest_data, colWidths=[50 * mm, doc.width - 50 * mm])
    attest_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#1e293b")),
        ("BACKGROUND",    (1, 0), (1, -1), CARD_BG),
        ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
        ("TEXTCOLOR",     (0, 0), (0, -1), CYAN),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#334155")),
    ]))
    story.append(attest_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── 2. Résumé par domaine ─────────────────────────────────────────────
    story.append(Paragraph("2. Résumé par domaine", styles["section"]))
    story.append(section_rule(doc.width, "nis2"))
    story.append(Spacer(1, 3 * mm))

    summary_rows = [["Domaine", "Score", "Statut"]]
    for dom, pct in domain_scores:
        status = "Conforme" if pct >= 80 else "Partiel" if pct >= 50 else "Non conforme"
        summary_rows.append([dom, f"{pct} %", status])

    summary_tbl = Table(summary_rows, colWidths=[doc.width * 0.55, doc.width * 0.15, doc.width * 0.30])
    summary_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("BACKGROUND",    (0, 1), (-1, -1), CARD_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), CYAN),
        ("TEXTCOLOR",     (0, 1), (-1, -1), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#334155")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, colors.HexColor("#1a2535")]),
    ]))
    story.append(summary_tbl)
    story.append(Spacer(1, 6 * mm))

    # ── 3. Détail par catégorie ───────────────────────────────────────────
    story.append(Paragraph("3. Détail des contrôles par catégorie", styles["section"]))
    story.append(section_rule(doc.width, "nis2"))
    story.append(Spacer(1, 3 * mm))

    for cat in categories:
        story.append(Paragraph(cat.get("label", cat.get("name", "")), styles["subsection"]))
        rows = [["Contrôle", "Statut"]]
        for item in cat["items"]:
            st = items.get(item["id"], "non_compliant")
            rows.append([item["label"], STATUS_LABEL.get(st, st)])

        det_tbl = Table(rows, colWidths=[doc.width * 0.75, doc.width * 0.25])
        cell_colors = []
        for i, item in enumerate(cat["items"], start=1):
            st = items.get(item["id"], "non_compliant")
            col = STATUS_COLOR.get(st, GRAY)
            cell_colors.append(("TEXTCOLOR", (1, i), (1, i), col))

        det_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), CYAN),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND",    (0, 1), (-1, -1), CARD_BG),
            ("TEXTCOLOR",     (0, 1), (0, -1), WHITE),
            ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, colors.HexColor("#1a2535")]),
            *cell_colors,
        ]))
        story.append(det_tbl)
        story.append(Spacer(1, 4 * mm))

    # ── 4. Plan d'action ──────────────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("4. Plan d'action — mesures prioritaires", styles["section"]))
    story.append(section_rule(doc.width, "nis2"))
    story.append(Spacer(1, 3 * mm))

    non_compliant_items = [
        (cat.get("label", cat.get("name", "")), item, items.get(item["id"], "non_compliant"))
        for cat in categories
        for item in cat["items"]
        if items.get(item["id"], "non_compliant") in ("non_compliant", "partial")
    ]
    non_compliant_items.sort(key=lambda x: 0 if x[2] == "non_compliant" else 1)

    if non_compliant_items:
        plan_rows = [["Domaine", "Mesure", "Priorité", "Statut actuel"]]
        for cat_name, item, st in non_compliant_items:
            prio = _PRIORITY.get(st, "—")
            plan_rows.append([cat_name, item["label"], prio, STATUS_LABEL.get(st, st)])

        prio_colors = []
        for i, (_, _, st) in enumerate(non_compliant_items, start=1):
            prio = _PRIORITY.get(st, "—")
            col = _PRIORITY_COL.get(prio, GRAY)
            prio_colors.append(("TEXTCOLOR", (2, i), (2, i), col))
            prio_colors.append(("FONTNAME",  (2, i), (2, i), "Helvetica-Bold"))

        plan_tbl = Table(
            plan_rows,
            colWidths=[doc.width * 0.22, doc.width * 0.45, doc.width * 0.15, doc.width * 0.18],
        )
        plan_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR",     (0, 0), (-1, 0), CYAN),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("BACKGROUND",    (0, 1), (-1, -1), CARD_BG),
            ("TEXTCOLOR",     (0, 1), (-1, -1), WHITE),
            ("FONTSIZE",      (0, 0), (-1, -1), 7.5),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 6),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [CARD_BG, colors.HexColor("#1a2535")]),
            *prio_colors,
        ]))
        story.append(plan_tbl)
    else:
        story.append(Paragraph("Tous les contrôles sont conformes ou non applicables.", styles["body"]))

    story.append(Spacer(1, 8 * mm))

    # ── 5. Déclaration de l'auditeur ─────────────────────────────────────
    story.append(Paragraph("5. Déclaration et attestation", styles["section"]))
    story.append(section_rule(doc.width, "nis2"))
    story.append(Spacer(1, 3 * mm))

    decl_text = (
        "Le soussigné atteste que l'évaluation de conformité à la Directive NIS2 a été réalisée "
        f"le {today_str}, sur la base des informations communiquées par l'entité évaluée. "
        "Ce document a été généré via la plateforme CyberScan (cyberscanapp.com) et reflète "
        "l'état de conformité auto-évalué à la date indiquée. "
        "Il est destiné à servir de base documentaire lors d'un audit de conformité NIS2 ou "
        "d'une déclaration auprès de l'ANSSI."
    )
    story.append(Paragraph(decl_text, styles["body"]))
    story.append(Spacer(1, 12 * mm))

    sig_data = [
        ["Nom / Prénom", ""],
        ["Fonction", ""],
        ["Date", today_str],
        ["Signature", ""],
    ]
    sig_tbl = Table(sig_data, colWidths=[45 * mm, doc.width - 45 * mm])
    sig_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), colors.HexColor("#1e293b")),
        ("BACKGROUND",    (1, 0), (1, -1), CARD_BG),
        ("TEXTCOLOR",     (0, 0), (-1, -1), WHITE),
        ("TEXTCOLOR",     (0, 0), (0, -1), CYAN),
        ("FONTNAME",      (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#334155")),
    ]))
    story.append(sig_tbl)

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
    return buf.getvalue()
