"""
Generate a PDF report for a URL scan result.
Uses shared visual identity from pdf_brand.
"""

from __future__ import annotations

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
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
    GRAY,
    GREEN,
    ORANGE,
    RED,
    WHITE,
    YELLOW,
    draw_page, draw_url_scan_cover,
    get_styles,
    section_rule,
)

DOC_TYPE = "url"

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
VERDICT_HEX = {
    "safe":       "#4ade80",
    "suspicious": "#facc15",
    "malicious":  "#f87171",
}
SEVERITY_COLOR = {
    "critical": RED,
    "high":     ORANGE,
    "medium":   YELLOW,
    "low":      GRAY,
}
SEVERITY_LABEL = {
    "critical": "Critique",
    "high":     "Élevé",
    "medium":   "Moyen",
    "low":      "Faible",
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
        topMargin=25 * mm,
        bottomMargin=20 * mm,
    )

    W  = A4[0] - 30 * mm
    st = get_styles(DOC_TYPE)

    # ── Extract scan data needed for cover + content ───────────────────────────
    verdict       = url_scan_data.get("verdict") or "unknown"
    score         = url_scan_data.get("threat_score") or 0
    v_label       = VERDICT_LABEL.get(verdict, verdict.upper())
    v_hex         = VERDICT_HEX.get(verdict, "#94a3b8")
    findings      = url_scan_data.get("findings") or []
    redirect_count = url_scan_data.get("redirect_count", 0)
    ssl_valid     = url_scan_data.get("ssl_valid", True)
    url           = url_scan_data.get("url", "")

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

    # Cover is page 1 (drawn by onFirstPage). Content starts on page 2.
    story: list = [PageBreak()]

    # ── URL info ──────────────────────────────────────────────────────────────
    orig_domain  = url_scan_data.get("original_domain", "")
    final_domain = url_scan_data.get("final_domain", "")

    url_color    = "#06b6d4"
    domain_color = "#facc15" if final_domain != orig_domain else "#ffffff"

    info_rows = [
        ["URL analysée",      Paragraph(
            f'<font name="Courier" size="8" color="{url_color}">{url}</font>',
            st["body"],
        )],
        ["Domaine d'origine", orig_domain],
        ["Domaine final",     Paragraph(
            f'<font color="{domain_color}">{final_domain}</font>',
            st["body"],
        )],
        ["SSL",               "&#10004; Valide" if ssl_valid else "&#10008; Invalide / Expiré"],
        ["Redirections",      str(redirect_count)],
        ["Date d'analyse",    date_str],
    ]

    info_table = Table(info_rows, colWidths=[W * 0.28, W * 0.72])
    info_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, -1), DARK_BG),
        ("BACKGROUND",    (1, 0), (1, -1), CARD_BG),
        ("TEXTCOLOR",     (0, 0), (0, -1), GRAY),
        ("TEXTCOLOR",     (1, 0), (1, -1), WHITE),
        ("FONTNAME",      (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
        ("ROUNDEDCORNERS", [4]),
        ("TEXTCOLOR",     (1, 3), (1, 3), GREEN if ssl_valid else RED),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 6 * mm))

    # ── Findings ──────────────────────────────────────────────────────────────
    story.append(Paragraph(f"Comportements détectés ({len(findings)})", st["section"]))
    story.append(section_rule(W, DOC_TYPE))

    if not findings:
        story.append(Paragraph("Aucun comportement suspect détecté.", st["body"]))
    else:
        finding_rows = [["Sévérité", "Détail"]]
        for f in findings:
            sev       = f.get("severity", "low")
            sev_color = SEVERITY_COLOR.get(sev, GRAY)
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
            ("TEXTCOLOR",     (0, 0), (-1, 0), GRAY),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 8),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 10),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
            ("GRID",          (0, 0), (-1, -1), 0.3, BORDER),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(finding_table)

    story.append(Spacer(1, 6 * mm))

    # ── Redirect chain ────────────────────────────────────────────────────────
    redirect_chain = url_scan_data.get("redirect_chain") or []
    if redirect_chain:
        story.append(Paragraph("Chaîne de redirections", st["section"]))
        story.append(section_rule(W, DOC_TYPE))
        for i, hop in enumerate(redirect_chain):
            story.append(Paragraph(f"{'&#8594; ' if i > 0 else ''}{hop}", st["mono"]))
        story.append(Spacer(1, 4 * mm))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width=W, thickness=0.5, color=BORDER, spaceAfter=4))
    story.append(Paragraph(
        f"Rapport généré par CyberScan le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} UTC — "
        "Ce rapport est fourni à titre informatif uniquement.",
        st["small"],
    ))

    # ── Build ─────────────────────────────────────────────────────────────────
    def _first_page(c, d):
        draw_url_scan_cover(
            c, d,
            url=url,
            verdict_label=v_label,
            verdict_color_hex=v_hex,
            threat_score=score,
            findings_count=len(findings),
            redirect_count=redirect_count,
            ssl_valid=ssl_valid,
            date_str=date_str,
        )

    doc.build(
        story,
        onFirstPage=_first_page,
        onLaterPages=lambda c, d: draw_page(c, d, DOC_TYPE, "Analyse d'URL"),
    )
    return buf.getvalue()
