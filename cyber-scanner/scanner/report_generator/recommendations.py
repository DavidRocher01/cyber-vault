"""recommendations.py — prioritised remediation recommendations builder."""

from __future__ import annotations

from typing import Any

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from scanner.constants import HEADER_RECOMMENDATIONS, PORT_NAMES

from .theme import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_TEXT,
    _section_header,
    _status_bullet,
    _status_color,
)


# ---------------------------------------------------------------------------
# Section 24 — Recommandations
# ---------------------------------------------------------------------------
def _build_recommendations(
    ssl_result: dict[str, Any],
    headers_result: dict[str, Any],
    port_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    ports_skipped: bool = False,
    sca_result: dict[str, Any] | None = None,
    sca_skipped: bool = True,
) -> list:
    story = []
    story += _section_header(24, "Recommandations", styles)

    recommendations: list[tuple[str, str]] = []  # (priority, text)

    # SSL recommendations
    if ssl_result:
        ssl_status = ssl_result.get("status", "OK")
        tls_ok = ssl_result.get("tls_ok", True)
        if ssl_result.get("error") or ssl_status in ("CRITICAL", "WARNING"):
            recommendations.append(
                (
                    "CRITICAL",
                    "Renouveler le certificat SSL via Let's Encrypt (certbot renew)",
                )
            )
        if not tls_ok:
            recommendations.append(
                (
                    "WARNING",
                    "Mettre à niveau vers TLS 1.2 minimum — désactiver TLS 1.0 et 1.1 dans la configuration serveur",
                )
            )

    # Header recommendations
    if headers_result and not headers_result.get("error"):
        for header in headers_result.get("headers_missing", []):
            rec = HEADER_RECOMMENDATIONS.get(header)
            if rec:
                recommendations.append(("WARNING", rec))

    # SCA recommendations
    if not sca_skipped and sca_result and not sca_result.get("error"):
        for vuln in sca_result.get("vulns", []):
            sev = vuln.get("severity", "UNKNOWN")
            cve_str = ", ".join(vuln.get("cve_ids", ["N/A"]))
            recommendations.append(
                (
                    "CRITICAL" if sev in ("CRITICAL", "HIGH") else "WARNING",
                    f"Mettre à jour {vuln['package']} ({vuln['version']}) — {cve_str} : {vuln['summary'][:120]}",
                )
            )

    # Port recommendations
    if not ports_skipped and port_result and not port_result.get("error"):
        critical_ports = port_result.get("critical_ports", [])
        if critical_ports:
            ports_str = ", ".join(
                f"{p} ({PORT_NAMES.get(p, 'unknown')})" for p in critical_ports
            )
            recommendations.append(
                (
                    "CRITICAL",
                    f"Fermer les ports {ports_str} exposés publiquement via pare-feu (ufw deny <port>)",
                )
            )

    if not recommendations:
        story.append(
            Paragraph(
                "Aucune recommandation critique. Maintenez vos configurations à jour et effectuez des audits réguliers.",
                styles["body"],
            )
        )
        return story

    priority_order = {"CRITICAL": 0, "WARNING": 1, "OK": 2}
    recommendations.sort(key=lambda x: priority_order.get(x[0], 99))

    col_w = page_w - 4 * cm

    for priority, text in recommendations:
        c = _status_color(priority)
        priority_label = _status_bullet(priority)
        badge_style = ParagraphStyle(
            "pb24",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=c,
            alignment=TA_CENTER,
        )
        text_style = ParagraphStyle(
            "pt24",
            fontName="Helvetica",
            fontSize=10,
            textColor=COLOR_TEXT,
        )
        row_table = Table(
            [[Paragraph(priority_label, badge_style), Paragraph(text, text_style)]],
            colWidths=[2.5 * cm, col_w - 2.5 * cm],
        )
        row_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), COLOR_CARD),
                    ("BACKGROUND", (1, 0), (1, 0), COLOR_BG),
                    ("BOX", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.append(row_table)
        story.append(Spacer(1, 0.2 * cm))

    return story
