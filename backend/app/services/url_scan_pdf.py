"""
Generate a PDF report for a URL scan result.
Uses ReportLab — already a transitive dependency via qrcode[pil].
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


# ── colour palette ──────────────────────────────────────────────────────────
DARK_BG    = colors.HexColor("#111827")
CARD_BG    = colors.HexColor("#1f2937")
CYAN       = colors.HexColor("#22d3ee")
GREEN      = colors.HexColor("#4ade80")
YELLOW     = colors.HexColor("#facc15")
RED        = colors.HexColor("#f87171")
ORANGE     = colors.HexColor("#fb923c")
GRAY_TEXT  = colors.HexColor("#9ca3af")
WHITE      = colors.white

VERDICT_COLOR = {
    "safe":       GREEN,
    "suspicious": YELLOW,
    "malicious":  RED,
}
VERDICT_LABEL = {
    "safe":       "SÛR",
    "suspicious": "SUSPECT",
    "malicious":  "MALVEILLANT",
}
SEVERITY_COLOR = {
    "critical": RED,
    "high":     ORANGE,
    "medium":   YELLOW,
    "low":      GRAY_TEXT,
}
SEVERITY_LABEL = {
    "critical": "Critique",
    "high":     "Élevé",
    "medium":   "Moyen",
    "low":      "Faible",
}


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title",
            fontSize=22,
            textColor=WHITE,
            fontName="Helvetica-Bold",
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            fontSize=10,
            textColor=GRAY_TEXT,
            fontName="Helvetica",
            spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "Section",
            fontSize=11,
            textColor=CYAN,
            fontName="Helvetica-Bold",
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            fontSize=9,
            textColor=WHITE,
            fontName="Helvetica",
            spaceAfter=2,
        ),
        "small": ParagraphStyle(
            "Small",
            fontSize=8,
            textColor=GRAY_TEXT,
            fontName="Helvetica",
        ),
        "mono": ParagraphStyle(
            "Mono",
            fontSize=8,
            textColor=CYAN,
            fontName="Courier",
            spaceAfter=2,
        ),
        "verdict": ParagraphStyle(
            "Verdict",
            fontSize=28,
            fontName="Helvetica-Bold",
        ),
    }


def generate_url_scan_pdf(url_scan_data: dict) -> bytes:
    """
    Generate a PDF report for a completed URL scan.

    url_scan_data must contain:
        url, verdict, threat_type, threat_score,
        ssl_valid, original_domain, final_domain,
        redirect_count, redirect_chain, findings,
        created_at (ISO string or datetime)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    W = A4[0] - 30 * mm  # usable width
    st = _styles()
    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    header_data = [[
        Paragraph("CyberScan", st["title"]),
        Paragraph("Rapport d'analyse URL", st["subtitle"]),
    ]]
    header_table = Table(header_data, colWidths=[W * 0.5, W * 0.5])
    header_table.setStyle(TableStyle([
        ("BACKGROUND",  (0, 0), (-1, -1), DARK_BG),
        ("TOPPADDING",  (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ("LEFTPADDING",   (0, 0), (-1, -1), 12),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 12),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    # ── Verdict hero ──────────────────────────────────────────────────────────
    verdict = url_scan_data.get("verdict") or "unknown"
    score   = url_scan_data.get("threat_score") or 0
    v_color = VERDICT_COLOR.get(verdict, GRAY_TEXT)
    v_label = VERDICT_LABEL.get(verdict, verdict.upper())

    verdict_style = ParagraphStyle(
        "VerdictDyn",
        fontSize=28,
        fontName="Helvetica-Bold",
        textColor=v_color,
    )
    score_style = ParagraphStyle(
        "ScoreDyn",
        fontSize=13,
        fontName="Helvetica-Bold",
        textColor=v_color,
    )
    threat_type = url_scan_data.get("threat_type") or ""
    threat_label_map = {
        "phishing":          "Phishing",
        "malware":           "Malware",
        "redirect":          "Redirection suspecte",
        "tracker":           "Tracker",
        "malicious_domain":  "Domaine malveillant",
    }
    threat_label = threat_label_map.get(threat_type, threat_type) if threat_type else ""

    verdict_data = [[
        Paragraph(v_label, verdict_style),
        Paragraph(f"Score : {score}/100<br/><font size='9' color='#9ca3af'>{threat_label}</font>", score_style),
    ]]
    verdict_table = Table(verdict_data, colWidths=[W * 0.6, W * 0.4])
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), CARD_BG),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("LEFTPADDING",   (0, 0), (-1, -1), 14),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 14),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN",         (1, 0), (1, 0),   "RIGHT"),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(verdict_table)
    story.append(Spacer(1, 5 * mm))

    # ── URL info ──────────────────────────────────────────────────────────────
    url         = url_scan_data.get("url", "")
    orig_domain = url_scan_data.get("original_domain", "")
    final_domain = url_scan_data.get("final_domain", "")
    redirect_count = url_scan_data.get("redirect_count", 0)
    ssl_valid   = url_scan_data.get("ssl_valid", True)

    created_at = url_scan_data.get("created_at", "")
    if isinstance(created_at, datetime):
        date_str = created_at.strftime("%d/%m/%Y à %H:%M")
    elif created_at:
        try:
            dt = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            date_str = dt.strftime("%d/%m/%Y à %H:%M")
        except Exception:
            date_str = str(created_at)
    else:
        date_str = "—"

    info_rows = [
        ["URL analysée",     Paragraph(f'<font name="Courier" size="8" color="#22d3ee">{url}</font>', st["body"])],
        ["Domaine d'origine", orig_domain],
        ["Domaine final",    Paragraph(
            f'<font color="{"#facc15" if final_domain != orig_domain else "#ffffff"}">{final_domain}</font>',
            st["body"],
        )],
        ["SSL",              "✔ Valide" if ssl_valid else "✘ Invalide / Expiré"],
        ["Redirections",     str(redirect_count)],
        ["Date d'analyse",   date_str],
    ]

    info_table = Table(info_rows, colWidths=[W * 0.28, W * 0.72])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), DARK_BG),
        ("BACKGROUND",    (1, 0), (1, -1), CARD_BG),
        ("TEXTCOLOR",     (0, 0), (0, -1), GRAY_TEXT),
        ("TEXTCOLOR",     (1, 0), (1, -1), WHITE),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#374151")),
        ("ROUNDEDCORNERS", [4]),
        # SSL row colour
        ("TEXTCOLOR",     (1, 3), (1, 3), GREEN if ssl_valid else RED),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    # ── Findings ──────────────────────────────────────────────────────────────
    findings = url_scan_data.get("findings") or []
    story.append(Paragraph(f"Comportements détectés ({len(findings)})", st["section"]))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#374151"), spaceAfter=4))

    if not findings:
        story.append(Paragraph("Aucun comportement suspect détecté.", st["body"]))
    else:
        finding_rows = [["Sévérité", "Détail"]]
        for f in findings:
            sev = f.get("severity", "low")
            sev_color = SEVERITY_COLOR.get(sev, GRAY_TEXT)
            sev_label = SEVERITY_LABEL.get(sev, sev.capitalize())
            sev_style = ParagraphStyle(
                f"Sev_{sev}",
                fontSize=8,
                fontName="Helvetica-Bold",
                textColor=sev_color,
            )
            finding_rows.append([
                Paragraph(sev_label, sev_style),
                Paragraph(f.get("detail", ""), st["body"]),
            ])

        finding_table = Table(finding_rows, colWidths=[W * 0.18, W * 0.82])
        finding_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), DARK_BG),
            ("BACKGROUND",    (0, 1), (-1, -1), CARD_BG),
            ("TEXTCOLOR",     (0, 0), (-1, 0), GRAY_TEXT),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#374151")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(finding_table)

    story.append(Spacer(1, 6 * mm))

    # ── Redirect chain ────────────────────────────────────────────────────────
    redirect_chain = url_scan_data.get("redirect_chain") or []
    if redirect_chain:
        story.append(Paragraph("Chaîne de redirections", st["section"]))
        story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#374151"), spaceAfter=4))
        for i, hop in enumerate(redirect_chain):
            story.append(Paragraph(f"{'→ ' if i > 0 else ''}{hop}", st["mono"]))
        story.append(Spacer(1, 4 * mm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=colors.HexColor("#374151"), spaceAfter=4))
    story.append(Paragraph(
        f"Rapport généré par CyberScan le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre informatif uniquement.",
        st["small"],
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    def _on_page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(DARK_BG)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return buf.getvalue()
