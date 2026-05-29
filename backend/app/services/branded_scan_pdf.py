"""
branded_scan_pdf.py — White-label management summary PDF for a scan result.

Generates a concise executive-level report (cover + findings summary) using the
client's company name, accent color, and optional base64 logo.
"""

from __future__ import annotations

import base64
import io
import json
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.pdf_brand import (
    BORDER,
    CARD_BG,
    CYAN,
    DARK_BG,
    FOOTER_H,
    GRAY,
    GREEN,
    MARGIN,
    PAGE_H,
    PAGE_W,
    RED,
    WHITE,
    YELLOW,
    get_styles,
    section_rule,
)

_STATUS_COLOR = {
    "OK": GREEN,
    "WARNING": YELLOW,
    "CRITICAL": RED,
}

_STATUS_LABEL = {
    "OK": "Aucune vulnérabilité critique",
    "WARNING": "Vulnérabilités à corriger",
    "CRITICAL": "Action immédiate requise",
}


def _accent(hex_color: str) -> colors.Color:
    try:
        return colors.HexColor(hex_color)
    except Exception:
        return CYAN


# ---------------------------------------------------------------------------
# Cover page (custom-branded)
# ---------------------------------------------------------------------------


def _draw_branded_cover(
    canvas,
    doc,
    *,
    company_name: str,
    accent_hex: str,
    logo_b64: str | None,
    domain: str,
    overall_status: str,
    score_pct: int,
    date_str: str,
    critical_count: int,
    warning_count: int,
    info_count: int,
) -> None:
    W, H = PAGE_W, PAGE_H
    M = MARGIN * mm
    acc = _accent(accent_hex)

    canvas.saveState()

    # Background
    canvas.setFillColor(DARK_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)

    # Top band
    BAND_H = 18 * mm
    band_y = H - BAND_H
    band_cy = H - BAND_H / 2

    canvas.setFillColor(colors.HexColor("#0f0a28"))
    canvas.rect(0, band_y, W, BAND_H, fill=1, stroke=0)
    canvas.setFillColor(acc)
    canvas.rect(0, band_y, 2 * mm, BAND_H, fill=1, stroke=0)
    canvas.setStrokeColor(acc)
    canvas.setLineWidth(2.5)
    canvas.line(0, band_y, W, band_y)

    # Logo or company initials in band
    logo_drawn = False
    if logo_b64:
        try:
            img_data = base64.b64decode(logo_b64.split(",")[-1])
            img_io = io.BytesIO(img_data)
            logo_h = BAND_H * 0.75
            logo_w = logo_h * 3
            logo_x = M + 3 * mm
            logo_y = band_cy - logo_h / 2
            canvas.drawImage(
                img_io,
                logo_x,
                logo_y,
                width=logo_w,
                height=logo_h,
                preserveAspectRatio=True,
                mask="auto",
            )
            logo_drawn = True
        except Exception:
            pass

    if not logo_drawn:
        # Fallback: colored circle with initials
        cx = M + 5 * mm
        r = BAND_H * 0.22
        canvas.setFillColor(acc)
        canvas.circle(cx, band_cy, r, fill=1, stroke=0)
        initials = "".join(w[0].upper() for w in company_name.split()[:2]) or "?"
        canvas.setFillColor(DARK_BG)
        canvas.setFont("Helvetica-Bold", BAND_H * 0.30)
        canvas.drawCentredString(cx, band_cy - BAND_H * 0.07, initials[:2])

    # Company name in band
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", BAND_H * 0.55)
    canvas.drawString(M + 15 * mm, band_cy - BAND_H * 0.12, company_name)

    # Right: "Rapport de sécurité"
    canvas.setFillColor(acc)
    canvas.setFont("Helvetica-Bold", BAND_H * 0.45)
    canvas.drawRightString(W - M, band_cy + BAND_H * 0.10, "RAPPORT DE SÉCURITÉ")
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", BAND_H * 0.35)
    canvas.drawRightString(W - M, band_cy - BAND_H * 0.28, date_str[:10])

    # ── Title block ───────────────────────────────────────────────────────────
    _tx = M
    ty = H - 52 * mm

    canvas.setFillColor(acc)
    canvas.roundRect(M, ty - 12 * mm, 3 * mm, 22 * mm, radius=1 * mm, fill=1, stroke=0)

    canvas.setFillColor(acc)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawString(M + 7 * mm, ty, "Audit de cybersécurité")

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawString(M + 7 * mm, ty - 8 * mm, domain)

    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(M + 7 * mm, ty - 14 * mm, f"Généré le {date_str}  •  Confidentiel")

    # ── Status card ───────────────────────────────────────────────────────────
    card_y = H - 120 * mm
    card_h = 55 * mm
    card_w = W - 2 * M
    s_col = _STATUS_COLOR.get(overall_status, GRAY)

    canvas.setFillColor(acc)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(M, card_y + card_h + 4 * mm, "SYNTHÈSE DE L'AUDIT")

    canvas.setFillColor(colors.HexColor("#111c30"))
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(colors.HexColor("#1e2d4a"))
    canvas.setLineWidth(0.8)
    canvas.roundRect(M, card_y, card_w, card_h, radius=4 * mm, fill=0, stroke=1)
    canvas.setStrokeColor(s_col)
    canvas.setLineWidth(2 * mm)
    canvas.setLineCap(0)
    canvas.line(
        M + 4 * mm,
        card_y + card_h - 1 * mm,
        M + card_w - 4 * mm,
        card_y + card_h - 1 * mm,
    )

    # Score gauge (left 38%)
    left_w = card_w * 0.38
    cx2 = M + left_w / 2
    cy2 = card_y + card_h / 2 + 6 * mm
    r2 = 18 * mm

    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(11)
    canvas.setLineCap(0)
    p = canvas.beginPath()
    p.arc(cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2, startAng=0, extent=180)
    canvas.drawPath(p, stroke=1, fill=0)

    if score_pct > 0:
        fill_ext = min(score_pct / 100 * 180, 180)
        canvas.setStrokeColor(s_col)
        canvas.setLineWidth(11)
        p2 = canvas.beginPath()
        p2.arc(
            cx2 - r2,
            cy2 - r2,
            cx2 + r2,
            cy2 + r2,
            startAng=180 - fill_ext,
            extent=fill_ext,
        )
        canvas.drawPath(p2, stroke=1, fill=0)

    canvas.setFillColor(colors.HexColor("#141e30"))
    canvas.circle(cx2, cy2, r2 - 6 * mm, fill=1, stroke=0)
    canvas.setFillColor(s_col)
    canvas.setFont("Helvetica-Bold", 26)
    canvas.drawCentredString(cx2, cy2 - 3.5 * mm, f"{score_pct}%")
    canvas.setFillColor(s_col)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawCentredString(cx2, card_y + 10 * mm, _STATUS_LABEL.get(overall_status, "Inconnu"))
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 6.5)
    canvas.drawCentredString(cx2, card_y + 5.5 * mm, "Score de sécurité")

    sep_x = M + left_w + 4 * mm
    canvas.setStrokeColor(colors.HexColor("#1e293b"))
    canvas.setLineWidth(0.8)
    canvas.line(sep_x, card_y + 8 * mm, sep_x, card_y + card_h - 8 * mm)

    # KPI 3-cell row (right 62%)
    kpis = [
        (critical_count, "Critiques", RED, colors.HexColor("#2d0a0a")),
        (warning_count, "Avertis.", YELLOW, colors.HexColor("#1c1400")),
        (info_count, "Infos", CYAN, colors.HexColor("#0c1a2e")),
    ]
    gx0 = sep_x + 4 * mm
    gw = card_w * 0.62 - 12 * mm
    cell_w = gw / 3 - 2 * mm
    cell_h = card_h - 16 * mm

    for i, (val, lbl, k_col, bg) in enumerate(kpis):
        kx = gx0 + i * (cell_w + 3 * mm)
        ky = card_y + 8 * mm
        canvas.setFillColor(bg)
        canvas.roundRect(kx, ky, cell_w, cell_h, radius=2.5 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(k_col)
        canvas.setLineWidth(2 * mm)
        canvas.setLineCap(0)
        canvas.line(
            kx + 2.5 * mm,
            ky + cell_h - 1 * mm,
            kx + cell_w - 2.5 * mm,
            ky + cell_h - 1 * mm,
        )
        canvas.setFillColor(k_col)
        canvas.setFont("Helvetica-Bold", 22)
        canvas.drawCentredString(kx + cell_w / 2, ky + cell_h * 0.52, str(val))
        canvas.setFillColor(GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawCentredString(kx + cell_w / 2, ky + 3.5 * mm, lbl)

    # ── Domain analysé ────────────────────────────────────────────────────────
    url_y = card_y - 12 * mm
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica-Bold", 7)
    canvas.drawString(M, url_y + 2 * mm, "DOMAINE AUDITÉ")

    canvas.setFillColor(colors.HexColor("#0e1623"))
    canvas.roundRect(M, url_y - 8 * mm, card_w, 9 * mm, radius=2 * mm, fill=1, stroke=0)

    max_dom = 90
    short_dom = domain if len(domain) <= max_dom else domain[: max_dom - 1] + "…"
    canvas.setFillColor(CYAN)
    canvas.setFont("Courier", 8)
    canvas.drawString(M + 4 * mm, url_y - 3.5 * mm, short_dom)

    # ── Footer ────────────────────────────────────────────────────────────────
    fy = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, fy + 4 * mm, W - M, fy + 4 * mm)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, fy - 1 * mm, f"{company_name} — confidentiel")
    canvas.drawCentredString(W / 2, fy - 1 * mm, "Page 1")
    canvas.drawRightString(W - M, fy - 1 * mm, date_str[:10])

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Content pages
# ---------------------------------------------------------------------------


def _draw_branded_page(canvas, doc, *, company_name: str, accent_hex: str) -> None:
    acc = _accent(accent_hex)
    M = MARGIN * mm
    BAND_H = 14 * mm
    band_y = PAGE_H - BAND_H
    band_cy = PAGE_H - BAND_H / 2
    today = datetime.now().strftime("%d/%m/%Y")

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
    canvas.drawString(M + 3 * mm, band_cy - BAND_H * 0.12, company_name)

    canvas.setFillColor(acc)
    canvas.setFont("Helvetica-Bold", BAND_H * 0.45)
    canvas.drawRightString(PAGE_W - M, band_cy + BAND_H * 0.10, "RAPPORT DE SÉCURITÉ")
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", BAND_H * 0.35)
    canvas.drawRightString(PAGE_W - M, band_cy - BAND_H * 0.28, today)

    fy = FOOTER_H * mm
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(M, fy, PAGE_W - M, fy)
    canvas.setFillColor(GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(M, fy - 5 * mm, f"{company_name} — confidentiel")
    canvas.drawCentredString(PAGE_W / 2, fy - 5 * mm, f"Page {doc.page}")
    canvas.drawRightString(PAGE_W - M, fy - 5 * mm, today)

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_branded_pdf(
    *,
    company_name: str,
    accent_color: str,
    logo_b64: str | None,
    domain: str,
    overall_status: str,
    score_pct: int,
    scan_date: str,
    findings: list[dict[str, Any]],
) -> bytes:
    buf = io.BytesIO()
    M = MARGIN * mm
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=M,
        rightMargin=M,
        topMargin=(14 + 4) * mm,
        bottomMargin=(FOOTER_H + 6) * mm,
    )

    cover_kwargs = dict(
        company_name=company_name,
        accent_hex=accent_color,
        logo_b64=logo_b64,
        domain=domain,
        overall_status=overall_status,
        score_pct=score_pct,
        date_str=scan_date,
        critical_count=sum(1 for f in findings if f.get("severity") == "critical"),
        warning_count=sum(1 for f in findings if f.get("severity") == "warning"),
        info_count=sum(1 for f in findings if f.get("severity") == "info"),
    )
    page_kwargs = dict(company_name=company_name, accent_hex=accent_color)

    def on_cover(c, d):
        _draw_branded_cover(c, d, **cover_kwargs)

    def on_page(c, d):
        _draw_branded_page(c, d, **page_kwargs)

    acc = _accent(accent_color)
    styles = get_styles("scan")
    # Override section color with accent
    styles["section"].textColor = acc

    story: list = [PageBreak()]

    # ── Findings summary ──────────────────────────────────────────────────────
    story.append(Paragraph("Résumé des vulnérabilités", styles["section"]))
    story.append(section_rule(doc.width, "scan"))
    story.append(Spacer(1, 3 * mm))

    if not findings:
        story.append(Paragraph("Aucune vulnérabilité détectée.", styles["body"]))
    else:
        sev_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_findings = sorted(
            findings, key=lambda f: sev_order.get(f.get("severity", "info"), 99)
        )
        for f in sorted_findings[:20]:
            sev = f.get("severity", "info")
            sev_col = {"critical": RED, "warning": YELLOW, "info": CYAN}.get(sev, GRAY)
            sev_lbl = {"critical": "CRITIQUE", "warning": "AVERT.", "info": "INFO"}.get(
                sev, sev.upper()
            )
            title = f.get("title") or f.get("check") or "—"
            desc = f.get("description") or f.get("detail") or ""

            tbl = Table(
                [
                    [
                        Paragraph(sev_lbl, styles["small"]),
                        Paragraph(f"<b>{title}</b>", styles["label"]),
                    ]
                ],
                colWidths=[18 * mm, doc.width - 18 * mm],
            )
            tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
                        (
                            "ROWBACKGROUNDS",
                            (0, 0),
                            (0, -1),
                            [sev_col.clone(alpha=0.15)],
                        ),
                        ("TEXTCOLOR", (0, 0), (0, -1), sev_col),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("TOPPADDING", (0, 0), (-1, -1), 4),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                        ("ROUNDEDCORNERS", [3]),
                    ]
                )
            )
            story.append(tbl)

            if desc:
                story.append(Paragraph(desc[:300], styles["body"]))
            story.append(Spacer(1, 2 * mm))

    # ── Recommandations ───────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("Recommandations prioritaires", styles["section"]))
    story.append(section_rule(doc.width, "scan"))
    story.append(Spacer(1, 3 * mm))

    recs = [
        "Corriger toutes les vulnérabilités critiques en priorité (délai : 72h).",
        "Mettre en place une politique de mise à jour mensuelle des dépendances.",
        "Activer le chiffrement HTTPS avec un certificat à jour (TLS 1.2+ minimum).",
        "Revoir les en-têtes de sécurité HTTP (CSP, HSTS, X-Frame-Options).",
        "Effectuer un nouveau scan après correction pour valider les remédiation.",
    ]
    for rec in recs:
        story.append(Paragraph(f"• {rec}", styles["body"]))
        story.append(Spacer(1, 1.5 * mm))

    doc.build(story, onFirstPage=on_cover, onLaterPages=on_page)
    return buf.getvalue()


def _extract_findings(results_json: str | None) -> list[dict]:
    if not results_json:
        return []
    try:
        data = json.loads(results_json)
        findings = []
        checks = data.get("checks") or data.get("results") or []
        for c in checks:
            if isinstance(c, dict):
                findings.append(c)
        return findings
    except Exception:
        return []


def _compute_score(findings: list[dict], overall_status: str | None) -> int:
    if not findings:
        return 100 if overall_status == "OK" else 0
    critical = sum(1 for f in findings if f.get("severity") == "critical")
    warning = sum(1 for f in findings if f.get("severity") == "warning")
    deduction = critical * 15 + warning * 5
    return max(0, min(100, 100 - deduction))
