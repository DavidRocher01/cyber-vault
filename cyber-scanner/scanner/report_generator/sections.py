"""sections.py — per-probe report section builders (one flowable list each)."""

from __future__ import annotations

from typing import Any

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
)

from scanner.constants import PORT_NAMES

from .theme import (
    COLOR_CARD,
    COLOR_CRITICAL,
    COLOR_MUTED,
    COLOR_OK,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_WARNING,
    _kv_styles,
    _kv_table,
    _not_scanned_table,
    _section_header,
    _status_color,
    _status_inline,
    _std_table_style,
)


# ---------------------------------------------------------------------------
# Section 2 — SSL/TLS
# ---------------------------------------------------------------------------
def _build_ssl_section(
    ssl_result: dict[str, Any], styles: dict[str, Any], page_w: float
) -> list:
    story = []
    story += _section_header(2, "SSL / TLS", styles)

    head_style, cell_style = _kv_styles("2")

    if ssl_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline("CRITICAL")],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(ssl_result["error"]), cell_style),
            ],
        ]
    else:
        days = ssl_result.get("days_remaining", 0) or 0
        days_color = (
            COLOR_OK if days >= 30 else (COLOR_WARNING if days >= 7 else COLOR_CRITICAL)
        )
        days_style = ParagraphStyle(
            "dy2", fontName="Helvetica-Bold", fontSize=10, textColor=days_color
        )

        valid_text = "Oui" if ssl_result.get("valid") else "Non"
        valid_color = COLOR_OK if ssl_result.get("valid") else COLOR_CRITICAL
        valid_style = ParagraphStyle(
            "vl2", fontName="Helvetica-Bold", fontSize=10, textColor=valid_color
        )

        tls_ok = ssl_result.get("tls_ok", False)
        tls_text = "Oui (>= TLS 1.2)" if tls_ok else "Non (protocole obsolète)"
        tls_color = COLOR_OK if tls_ok else COLOR_CRITICAL
        tls_style = ParagraphStyle(
            "tl2", fontName="Helvetica-Bold", fontSize=10, textColor=tls_color
        )

        status = ssl_result.get("status", "CRITICAL")
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline(status)],
            [
                Paragraph("Certificat valide", cell_style),
                Paragraph(valid_text, valid_style),
            ],
            [
                Paragraph("Date d'expiration", cell_style),
                Paragraph(str(ssl_result.get("expiry_date", "—")), cell_style),
            ],
            [Paragraph("Jours restants", cell_style), Paragraph(str(days), days_style)],
            [
                Paragraph("Protocole", cell_style),
                Paragraph(str(ssl_result.get("protocol", "—")), cell_style),
            ],
            [Paragraph("TLS OK", cell_style), Paragraph(tls_text, tls_style)],
        ]

    col_w = page_w - 4 * cm
    t = _kv_table(rows, [col_w * 0.38, col_w * 0.62])
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 3 — HTTP Headers
# ---------------------------------------------------------------------------
def _build_headers_section(
    headers_result: dict[str, Any], styles: dict[str, Any], page_w: float
) -> list:
    story = []
    story += _section_header(3, "Headers HTTP", styles)

    head_style, cell_style = _kv_styles("3")

    if headers_result.get("error"):
        rows = [
            [Paragraph("Header", head_style), Paragraph("Statut", head_style)],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(headers_result["error"]), cell_style),
            ],
        ]
    else:
        rows = [
            [
                Paragraph("Header de sécurité", head_style),
                Paragraph("Présence", head_style),
            ]
        ]

        found = set(headers_result.get("headers_found", []))
        missing = set(headers_result.get("headers_missing", []))
        all_headers = list(found) + list(missing)

        for header in all_headers:
            if header in found:
                present_style = ParagraphStyle(
                    "ok3", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_OK
                )
                rows.append(
                    [
                        Paragraph(header, cell_style),
                        Paragraph("✓  Présent", present_style),
                    ]
                )
            else:
                absent_style = ParagraphStyle(
                    "cr3",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=COLOR_CRITICAL,
                )
                rows.append(
                    [
                        Paragraph(header, cell_style),
                        Paragraph("✗  Absent", absent_style),
                    ]
                )

        score = headers_result.get("score", 0)
        score_color = (
            COLOR_OK
            if score == 6
            else (COLOR_WARNING if score >= 4 else COLOR_CRITICAL)
        )
        score_style = ParagraphStyle(
            "sc3", fontName="Helvetica-Bold", fontSize=10, textColor=score_color
        )
        rows.append(
            [
                Paragraph(
                    "Score total",
                    ParagraphStyle(
                        "stb3",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=COLOR_TEXT,
                    ),
                ),
                Paragraph(f"{score}/6", score_style),
            ]
        )

    col_w = page_w - 4 * cm
    t = Table(rows, colWidths=[col_w * 0.65, col_w * 0.35])
    # Last row gets a slightly distinct bg to stand out as summary
    t.setStyle(
        _std_table_style(
            [
                ("BACKGROUND", (0, -1), (-1, -1), COLOR_CARD),
            ]
        )
    )
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 4 — Ports réseau
# ---------------------------------------------------------------------------
def _build_ports_section(
    port_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(4, "Ports réseau", styles)

    head_style, cell_style = _kv_styles("4")
    col_w = page_w - 4 * cm

    if skipped or port_result is None:
        rows = [
            [Paragraph("Résultat", head_style)],
            [Paragraph("Non scanné (option --skip-ports activée)", cell_style)],
        ]
        t = Table(rows, colWidths=[col_w])
    elif port_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline("CRITICAL")],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(port_result["error"]), cell_style),
            ],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        open_ports = port_result.get("open_ports", [])
        critical_ports = port_result.get("critical_ports", [])

        rows = [
            [
                Paragraph("Port", head_style),
                Paragraph("Service", head_style),
                Paragraph("Criticité", head_style),
            ]
        ]

        if open_ports:
            for port_info in open_ports:
                if isinstance(port_info, dict):
                    port_num = port_info.get("port", 0)
                    service = port_info.get(
                        "service", PORT_NAMES.get(port_num, "unknown")
                    )
                    crit_raw = port_info.get("criticality", "")
                    is_critical = crit_raw.lower() in (
                        "critique",
                        "critical",
                        "high",
                        "danger",
                    )
                else:
                    port_num = port_info
                    service = PORT_NAMES.get(port_num, "unknown")
                    is_critical = port_num in (critical_ports or [])
                crit_text = "Critique" if is_critical else "Normal"
                crit_style = ParagraphStyle(
                    "cp4",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=COLOR_CRITICAL if is_critical else COLOR_OK,
                )
                rows.append(
                    [
                        Paragraph(str(port_num), cell_style),
                        Paragraph(service, cell_style),
                        Paragraph(crit_text, crit_style),
                    ]
                )
        else:
            rows.append(
                [
                    Paragraph("—", cell_style),
                    Paragraph("Aucun port ouvert", cell_style),
                    Paragraph(
                        "● OK",
                        ParagraphStyle(
                            "ok4",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_OK,
                        ),
                    ),
                ]
            )

        t = Table(rows, colWidths=[col_w * 0.2, col_w * 0.5, col_w * 0.3])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 5 — SCA (Software Composition Analysis)
# ---------------------------------------------------------------------------
def _build_sca_section(
    sca_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(5, "SCA — Analyse des dépendances", styles)

    head_style, cell_style = _kv_styles("5")
    col_w = page_w - 4 * cm

    if skipped or not sca_result:
        rows = [
            [Paragraph("Résultat", head_style)],
            [
                Paragraph(
                    "Non scanné (utiliser --requirements ou --package-json pour activer)",
                    cell_style,
                )
            ],
        ]
        t = _kv_table(rows, [col_w])
        story.append(t)
        return story

    if sca_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [Paragraph("Statut", cell_style), _status_inline("CRITICAL")],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(sca_result["error"]), cell_style),
            ],
        ]
        t = _kv_table(rows, [col_w * 0.35, col_w * 0.65])
        story.append(t)
        return story

    vulns = sca_result.get("vulns", [])
    total_pkgs = sca_result.get("total_packages", 0)
    total_vulns = sca_result.get("total_vulns", 0)

    vuln_color = (
        COLOR_OK
        if total_vulns == 0
        else (
            COLOR_WARNING if sca_result.get("status") == "WARNING" else COLOR_CRITICAL
        )
    )
    vuln_style = ParagraphStyle(
        "vs5", fontName="Helvetica-Bold", fontSize=10, textColor=vuln_color
    )

    summary_rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        [
            Paragraph("Packages scannés", cell_style),
            Paragraph(str(total_pkgs), cell_style),
        ],
        [
            Paragraph("Vulnérabilités trouvées", cell_style),
            Paragraph(str(total_vulns), vuln_style),
        ],
    ]
    t_summary = _kv_table(summary_rows, [col_w * 0.45, col_w * 0.55])
    story.append(t_summary)

    if vulns:
        story.append(Spacer(1, 0.4 * cm))
        sev_colors = {
            "CRITICAL": COLOR_CRITICAL,
            "HIGH": COLOR_CRITICAL,
            "MEDIUM": COLOR_WARNING,
            "LOW": colors.HexColor("#3B82F6"),
            "UNKNOWN": COLOR_MUTED,
        }
        vuln_head = [
            Paragraph("Package", head_style),
            Paragraph("CVE / ID", head_style),
            Paragraph("Sévérité", head_style),
            Paragraph("Résumé", head_style),
        ]
        vuln_rows = [vuln_head]
        for v in vulns:
            sev = v.get("severity", "UNKNOWN")
            sc = sev_colors.get(sev, COLOR_MUTED)
            sev_cell_style = ParagraphStyle(
                "sc5", fontName="Helvetica-Bold", fontSize=9, textColor=sc
            )
            cve_str = "\n".join(v.get("cve_ids", ["N/A"]))
            summary_text = v.get("summary", "")[:180]
            vuln_rows.append(
                [
                    Paragraph(
                        f"{v['package']}\n{v['version']}",
                        ParagraphStyle(
                            "pkg5",
                            fontName="Helvetica",
                            fontSize=9,
                            textColor=COLOR_TEXT,
                        ),
                    ),
                    Paragraph(
                        cve_str,
                        ParagraphStyle(
                            "cv5",
                            fontName="Helvetica",
                            fontSize=9,
                            textColor=COLOR_TEXT,
                        ),
                    ),
                    Paragraph(sev, sev_cell_style),
                    Paragraph(
                        summary_text,
                        ParagraphStyle(
                            "sm5",
                            fontName="Helvetica",
                            fontSize=8,
                            textColor=COLOR_MUTED,
                        ),
                    ),
                ]
            )
        t_vulns = Table(
            vuln_rows,
            colWidths=[col_w * 0.18, col_w * 0.22, col_w * 0.14, col_w * 0.46],
        )
        t_vulns.setStyle(_std_table_style([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        story.append(t_vulns)

    return story


# ---------------------------------------------------------------------------
# Section 6 — Email Security
# ---------------------------------------------------------------------------
def _build_email_section(
    email_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(6, "Email Security (SPF / DKIM / DMARC)", styles)

    head_style, cell_style = _kv_styles("6")
    col_w = page_w - 4 * cm

    if skipped or not email_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    elif email_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(email_result["error"]), cell_style),
            ],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:

        def flag_cell(found: bool, ok_text: str, bad_text: str) -> Paragraph:
            if found:
                return Paragraph(
                    ok_text,
                    ParagraphStyle(
                        "ok6",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=COLOR_OK,
                    ),
                )
            return Paragraph(
                bad_text,
                ParagraphStyle(
                    "cr6",
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=COLOR_CRITICAL,
                ),
            )

        spf = email_result.get("spf", {})
        dkim = email_result.get("dkim", {})
        dmarc = email_result.get("dmarc", {})
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(email_result.get("status", "OK")),
            ],
            [
                Paragraph("SPF", cell_style),
                flag_cell(
                    spf.get("found", False),
                    f"Présent {'(strict)' if spf.get('strict') else '(~all)'}",
                    "Absent",
                ),
            ],
            [
                Paragraph("DKIM", cell_style),
                flag_cell(
                    dkim.get("found", False),
                    f"Présent (selector: {dkim.get('selector', '?')})",
                    "Non détecté",
                ),
            ],
            [
                Paragraph("DMARC", cell_style),
                flag_cell(
                    dmarc.get("found", False),
                    f"Présent (p={dmarc.get('policy', '?')})",
                    "Absent",
                ),
            ],
        ]
        for issue in email_result.get("issues", []):
            rows.append(
                [
                    Paragraph(
                        "Issue",
                        ParagraphStyle(
                            "is6",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_WARNING,
                        ),
                    ),
                    Paragraph(issue, cell_style),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.3, col_w * 0.7])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 7 — Cookie Security
# ---------------------------------------------------------------------------
def _build_cookie_section(
    cookie_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(7, "Cookie Security", styles)

    head_style, cell_style = _kv_styles("7")
    col_w = page_w - 4 * cm

    if skipped or not cookie_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    elif cookie_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(cookie_result["error"]), cell_style),
            ],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        issues = cookie_result.get("issues", [])
        rows = [[Paragraph("Cookie", head_style), Paragraph("Problème", head_style)]]
        if issues:
            for issue in issues:
                rows.append(
                    [
                        Paragraph(issue["cookie"], cell_style),
                        Paragraph(
                            issue["issue"],
                            ParagraphStyle(
                                "warn7",
                                fontName="Helvetica",
                                fontSize=10,
                                textColor=COLOR_WARNING,
                            ),
                        ),
                    ]
                )
        else:
            rows.append(
                [
                    Paragraph("—", cell_style),
                    Paragraph(
                        "Tous les cookies sont correctement sécurisés",
                        ParagraphStyle(
                            "ok7",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_OK,
                        ),
                    ),
                ]
            )

        summary_style = ParagraphStyle(
            "sm7", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_TEXT
        )
        total_issues = cookie_result.get("total_issues", 0)
        ic = (
            COLOR_OK
            if total_issues == 0
            else (
                COLOR_WARNING
                if cookie_result.get("status") == "WARNING"
                else COLOR_CRITICAL
            )
        )
        rows.append(
            [
                Paragraph("Total cookies", summary_style),
                Paragraph(str(cookie_result.get("total_cookies", 0)), cell_style),
            ]
        )
        rows.append(
            [
                Paragraph("Total issues", summary_style),
                Paragraph(
                    str(total_issues),
                    ParagraphStyle(
                        "tc7", fontName="Helvetica-Bold", fontSize=10, textColor=ic
                    ),
                ),
            ]
        )
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])

    t.setStyle(
        _std_table_style(
            [
                ("BACKGROUND", (0, -2), (-1, -1), COLOR_CARD),
            ]
        )
    )
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 8 — CORS
# ---------------------------------------------------------------------------
def _build_cors_section(
    cors_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(8, "CORS", styles)

    head_style, cell_style = _kv_styles("8")
    col_w = page_w - 4 * cm

    if skipped or not cors_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    elif cors_result.get("error"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(cors_result["error"]), cell_style),
            ],
        ]
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])
    else:
        vuln = cors_result.get("vulnerable", False)
        vuln_style = ParagraphStyle(
            "vl8",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=COLOR_CRITICAL if vuln else COLOR_OK,
        )
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(cors_result.get("status", "OK")),
            ],
            [
                Paragraph("Allow-Origin", cell_style),
                Paragraph(cors_result.get("allow_origin") or "non défini", cell_style),
            ],
            [
                Paragraph("Allow-Credentials", cell_style),
                Paragraph(
                    cors_result.get("allow_credentials") or "non défini", cell_style
                ),
            ],
            [
                Paragraph("Vulnérable", cell_style),
                Paragraph("Oui" if vuln else "Non", vuln_style),
            ],
        ]
        for issue in cors_result.get("issues", []):
            rows.append(
                [
                    Paragraph(
                        "Issue",
                        ParagraphStyle(
                            "is8",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_WARNING,
                        ),
                    ),
                    Paragraph(issue, cell_style),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 9 — IP Réputation
# ---------------------------------------------------------------------------
def _build_ip_reputation_section(
    ip_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(9, "IP Réputation (DNSBL)", styles)

    head_style, cell_style = _kv_styles("9")
    col_w = page_w - 4 * cm

    if skipped or not ip_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    elif ip_result.get("error") and not ip_result.get("ip"):
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Erreur", cell_style),
                Paragraph(str(ip_result["error"]), cell_style),
            ],
        ]
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])
    else:
        listed = ip_result.get("listed_in", [])
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(ip_result.get("status", "OK")),
            ],
            [
                Paragraph("IP", cell_style),
                Paragraph(str(ip_result.get("ip", "—")), cell_style),
            ],
            [
                Paragraph("Blacklists", cell_style),
                Paragraph(
                    str(ip_result.get("total_listed", 0)),
                    ParagraphStyle(
                        "bl9",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=COLOR_CRITICAL if listed else COLOR_OK,
                    ),
                ),
            ],
        ]
        for entry in listed:
            rows.append(
                [
                    Paragraph(
                        entry["label"],
                        ParagraphStyle(
                            "lb9",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_CRITICAL,
                        ),
                    ),
                    Paragraph(entry["category"], cell_style),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 10 — DNS & Subdomains
# ---------------------------------------------------------------------------
def _build_dns_section(
    dns_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(10, "DNS & Subdomains", styles)

    head_style, cell_style = _kv_styles("10")
    col_w = page_w - 4 * cm

    if skipped or not dns_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    else:
        zt = dns_result.get("zone_transfer", {})
        zt_style = ParagraphStyle(
            "zt10",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=COLOR_CRITICAL if zt.get("vulnerable") else COLOR_OK,
        )
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(dns_result.get("status", "OK")),
            ],
            [
                Paragraph("Subdomains trouvés", cell_style),
                Paragraph(str(dns_result.get("total_found", 0)), cell_style),
            ],
            [
                Paragraph("Zone Transfer", cell_style),
                Paragraph("VULNERABLE" if zt.get("vulnerable") else "Refusé", zt_style),
            ],
        ]
        for s in dns_result.get("found", [])[:10]:
            rows.append(
                [
                    Paragraph(
                        s["subdomain"],
                        ParagraphStyle(
                            "sub10",
                            fontName="Helvetica",
                            fontSize=9,
                            textColor=COLOR_PRIMARY,
                        ),
                    ),
                    Paragraph(s["ip"], cell_style),
                ]
            )
        if dns_result.get("total_found", 0) > 10:
            rows.append(
                [
                    Paragraph(
                        f"... et {dns_result['total_found'] - 10} autres", cell_style
                    ),
                    Paragraph("", cell_style),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.55, col_w * 0.45])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 11 — CMS Detection
# ---------------------------------------------------------------------------
def _build_cms_section(
    cms_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(11, "CMS Detection", styles)

    head_style, cell_style = _kv_styles("11")
    col_w = page_w - 4 * cm

    if skipped or not cms_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    else:
        cms = cms_result.get("cms", "Unknown")
        version = cms_result.get("version")
        cms_color = (
            COLOR_OK
            if cms == "Unknown"
            else (COLOR_CRITICAL if version else COLOR_WARNING)
        )
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(cms_result.get("status", "OK")),
            ],
            [
                Paragraph("CMS détecté", cell_style),
                Paragraph(
                    cms,
                    ParagraphStyle(
                        "cms11",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=cms_color,
                    ),
                ),
            ],
        ]
        if version:
            rows.append(
                [
                    Paragraph("Version exposée", cell_style),
                    Paragraph(
                        version,
                        ParagraphStyle(
                            "ver11",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_CRITICAL,
                        ),
                    ),
                ]
            )
        rows.append(
            [
                Paragraph("Confidence", cell_style),
                Paragraph(str(cms_result.get("confidence", 0)), cell_style),
            ]
        )
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 12 — WAF Detection
# ---------------------------------------------------------------------------
def _build_waf_section(
    waf_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(12, "WAF Detection", styles)

    head_style, cell_style = _kv_styles("12")
    col_w = page_w - 4 * cm

    if skipped or not waf_result:
        t = _not_scanned_table(head_style, cell_style, col_w)
    else:
        detected = waf_result.get("detected", False)
        det_style = ParagraphStyle(
            "det12",
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=COLOR_OK if detected else COLOR_WARNING,
        )
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(waf_result.get("status", "OK")),
            ],
            [
                Paragraph("WAF détecté", cell_style),
                Paragraph("Oui" if detected else "Non", det_style),
            ],
        ]
        if waf_result.get("waf_name"):
            rows.append(
                [
                    Paragraph("Nom", cell_style),
                    Paragraph(
                        waf_result["waf_name"],
                        ParagraphStyle(
                            "wn12",
                            fontName="Helvetica-Bold",
                            fontSize=10,
                            textColor=COLOR_OK,
                        ),
                    ),
                ]
            )
        if waf_result.get("method"):
            rows.append(
                [
                    Paragraph("Méthode détection", cell_style),
                    Paragraph(waf_result["method"], cell_style),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.4, col_w * 0.6])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 13 — Data Breach
# ---------------------------------------------------------------------------
def _build_breach_section(
    breach_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(13, "Data Breach (HIBP)", styles)

    head_style, cell_style = _kv_styles("13")
    col_w = page_w - 4 * cm

    if skipped or not breach_result:
        rows = [
            [Paragraph("Résultat", head_style)],
            [
                Paragraph(
                    "Non scanné (utiliser --breach-email ou --breach-domain)",
                    cell_style,
                )
            ],
        ]
        t = Table(rows, colWidths=[col_w])
    elif breach_result.get("error") and breach_result.get("status") == "WARNING":
        rows = [
            [Paragraph("Résultat", head_style)],
            [Paragraph(str(breach_result["error"]), cell_style)],
        ]
        t = Table(rows, colWidths=[col_w])
    else:
        total = breach_result.get("total", 0)
        total_color = (
            COLOR_OK
            if total == 0
            else (
                COLOR_WARNING
                if breach_result.get("status") == "WARNING"
                else COLOR_CRITICAL
            )
        )
        rows = [
            [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
            [
                Paragraph("Statut", cell_style),
                _status_inline(breach_result.get("status", "OK")),
            ],
            [
                Paragraph("Cible", cell_style),
                Paragraph(breach_result.get("target", ""), cell_style),
            ],
            [
                Paragraph("Fuites trouvées", cell_style),
                Paragraph(
                    str(total),
                    ParagraphStyle(
                        "tc13",
                        fontName="Helvetica-Bold",
                        fontSize=10,
                        textColor=total_color,
                    ),
                ),
            ],
        ]
        for b in breach_result.get("breaches", []):
            rows.append(
                [
                    Paragraph(
                        b["name"],
                        ParagraphStyle(
                            "bn13",
                            fontName="Helvetica-Bold",
                            fontSize=9,
                            textColor=COLOR_CRITICAL,
                        ),
                    ),
                    Paragraph(
                        f"{b.get('breach_date', '')} — {b.get('pwn_count', 0):,} comptes",
                        cell_style,
                    ),
                ]
            )
        t = Table(rows, colWidths=[col_w * 0.35, col_w * 0.65])

    t.setStyle(_std_table_style())
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 14 — Technology Fingerprint
# ---------------------------------------------------------------------------
def _build_tech_section(
    tech_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(14, "Technology Fingerprint", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-tech).", styles["body"]))
        return story

    status = tech_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    head_style = ParagraphStyle(
        "th14", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [
            Paragraph("Catégorie", head_style),
            Paragraph("Technologies détectées", head_style),
        ]
    ]
    for cat, names in tech_result.get("technologies", {}).items():
        rows.append([cat.capitalize(), ", ".join(names)])
    if len(rows) == 1:
        rows.append(["—", "Aucune technologie identifiée"])

    col_w = page_w - 4 * cm
    t = _kv_table(rows, [col_w * 0.3, col_w * 0.7])
    story.append(t)

    if tech_result.get("error"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"⚠ {tech_result['error']}", styles["body"]))
    return story


# ---------------------------------------------------------------------------
# Section 15 — TLS Deep Audit
# ---------------------------------------------------------------------------
def _build_tls_section(
    tls_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(15, "Audit TLS approfondi", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-tls).", styles["body"]))
        return story

    status = tls_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    hsts = tls_result.get("hsts", {})
    rows = [
        [
            "Protocoles supportés",
            ", ".join(tls_result.get("supported_protocols", [])) or "—",
        ],
        [
            "Protocoles faibles",
            ", ".join(tls_result.get("weak_protocols", [])) or "Aucun",
        ],
        [
            "Chiffrements faibles",
            ", ".join(tls_result.get("weak_ciphers", [])) or "Aucun",
        ],
        ["HSTS", "Présent" if hsts.get("present") else "Absent"],
        ["HSTS max-age", str(hsts.get("max_age", "—"))],
        ["HSTS preload", "Oui" if hsts.get("preload") else "Non"],
    ]
    cert = tls_result.get("certificate")
    if cert:
        rows += [
            ["Cert subject", cert.get("subject", "—")],
            ["Cert issuer", cert.get("issuer", "—")],
            ["Cert expires", cert.get("not_after", "—")],
        ]

    col_w = page_w - 4 * cm
    t = _kv_table(rows, [col_w * 0.35, col_w * 0.65])
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 16 — Subdomain Takeover
# ---------------------------------------------------------------------------
def _build_takeover_section(
    takeover_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(16, "Subdomain Takeover", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-takeover).", styles["body"]))
        return story

    status = takeover_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))
    story.append(
        Paragraph(
            f"Sous-domaines vérifiés : {takeover_result.get('total_checked', 0)} — "
            f"Vulnérables : {takeover_result.get('total_vulnerable', 0)}",
            styles["body"],
        )
    )

    vulns = takeover_result.get("vulnerable", [])
    if vulns:
        story.append(Spacer(1, 0.2 * cm))
        head_style = ParagraphStyle(
            "th16", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
        )
        rows = [
            [
                Paragraph("Sous-domaine", head_style),
                Paragraph("Service", head_style),
                Paragraph("Raison", head_style),
            ]
        ]
        for v in vulns:
            rows.append([v["subdomain"], v.get("service", "—"), v.get("reason", "—")])
        col_w = page_w - 4 * cm
        t = Table(rows, colWidths=[col_w * 0.38, col_w * 0.22, col_w * 0.40])
        # Takeover header gets critical color to signal danger
        t.setStyle(
            _std_table_style(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#3d1515")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_CRITICAL),
                ]
            )
        )
        story.append(t)

    if takeover_result.get("error"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(takeover_result["error"], styles["body"]))
    return story


# ---------------------------------------------------------------------------
# Section 17 — Threat Intelligence
# ---------------------------------------------------------------------------
def _build_threat_intel_section(
    ti_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(17, "Threat Intelligence (Shodan)", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-threat).", styles["body"]))
        return story

    status = ti_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    cves = ti_result.get("cves", [])
    ports = ti_result.get("open_ports", [])
    abuse = ti_result.get("abuse_score")

    head_style = ParagraphStyle(
        "th17", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["IP", str(ti_result.get("ip", "—"))],
        ["Ports ouverts", ", ".join(str(p) for p in ports) if ports else "—"],
        [
            "CVEs",
            ", ".join(cves[:8]) + ("…" if len(cves) > 8 else "") if cves else "Aucun",
        ],
        ["Tags Shodan", ", ".join(ti_result.get("tags", [])) or "—"],
        ["Abuse score", f"{abuse}/100" if abuse is not None else "—"],
    ]
    col_w = page_w - 4 * cm
    t = _kv_table(rows, [col_w * 0.3, col_w * 0.7])
    story.append(t)

    if ti_result.get("error"):
        story.append(Spacer(1, 0.2 * cm))
        story.append(Paragraph(f"⚠ {ti_result['error']}", styles["body"]))
    return story


# ---------------------------------------------------------------------------
# Section 18 — HTTP Methods
# ---------------------------------------------------------------------------
def _build_http_methods_section(
    methods_result: dict[str, Any],
    styles: dict[str, Any],
    page_w: float,
    skipped: bool = False,
) -> list:
    story = []
    story += _section_header(18, "Méthodes HTTP dangereuses", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-methods).", styles["body"]))
        return story

    status = methods_result.get("status", "OK")
    story.append(_status_inline(status))
    story.append(Spacer(1, 0.3 * cm))

    dangerous = methods_result.get("dangerous_allowed", [])
    allowed = methods_result.get("allowed_methods", [])
    declared = methods_result.get("options_declared", [])

    head_style = ParagraphStyle(
        "th18", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["OPTIONS déclare", ", ".join(declared) if declared else "—"],
        ["Méthodes autorisées", ", ".join(allowed) if allowed else "Aucune"],
        ["Méthodes dangereuses", ", ".join(dangerous) if dangerous else "Aucune"],
    ]
    col_w = page_w - 4 * cm
    t = _kv_table(rows, [col_w * 0.35, col_w * 0.65])
    story.append(t)

    probes = methods_result.get("probes", [])
    if probes:
        story.append(Spacer(1, 0.3 * cm))
        probe_head = [
            Paragraph("Méthode", head_style),
            Paragraph("Code HTTP", head_style),
            Paragraph("Acceptée", head_style),
        ]
        probe_rows = [probe_head]
        for p in probes:
            code = str(p["status_code"]) if p["status_code"] else "Erreur"
            accepted = "OUI" if p["allowed"] else "non"
            accepted_style = ParagraphStyle(
                "acc18",
                fontName="Helvetica-Bold",
                fontSize=9,
                textColor=COLOR_CRITICAL if p["allowed"] else COLOR_OK,
            )
            probe_rows.append(
                [
                    p["method"],
                    code,
                    Paragraph(accepted, accepted_style),
                ]
            )
        t2 = _kv_table(probe_rows, [col_w * 0.25, col_w * 0.35, col_w * 0.40])
        story.append(t2)
    return story


# ---------------------------------------------------------------------------
# Section 19 — Open Redirect
# ---------------------------------------------------------------------------
def _build_open_redirect_section(
    r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False
) -> list:
    story = []
    story += _section_header(19, "Open Redirect", styles)

    if skipped:
        story.append(
            Paragraph("Module non exécuté (--skip-redirects).", styles["body"])
        )
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    col_w = page_w - 4 * cm
    head_style = ParagraphStyle(
        "th19", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    vuln_text = "OUI" if r.get("vulnerable") else "Non"
    vuln_style = ParagraphStyle(
        "vl19",
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=COLOR_CRITICAL if r.get("vulnerable") else COLOR_OK,
    )
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["Probes envoyées", str(r.get("tested", 0))],
        ["Vulnérable", Paragraph(vuln_text, vuln_style)],
    ]
    findings = r.get("findings", [])
    for f in findings:
        rows.append([f"Param: {f['param']}", f"→ {f['location'][:60]}"])

    t = _kv_table(rows, [col_w * 0.35, col_w * 0.65])
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 20 — Clickjacking
# ---------------------------------------------------------------------------
def _build_clickjacking_section(
    r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False
) -> list:
    story = []
    story += _section_header(20, "Clickjacking", styles)

    if skipped:
        story.append(
            Paragraph("Module non exécuté (--skip-clickjacking).", styles["body"])
        )
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    xfo = r.get("xfo", {})
    csp = r.get("csp_frame_ancestors", {})
    col_w = page_w - 4 * cm

    head_style = ParagraphStyle(
        "th20", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["X-Frame-Options", xfo.get("value") or "Absent"],
        ["XFO protégé", "Oui" if xfo.get("protected") else "Non"],
        ["CSP frame-ancestors", csp.get("value") or "Absent"],
        ["CSP protégé", "Oui" if csp.get("protected") else "Non"],
        ["Vulnérable clickjacking", "OUI" if r.get("vulnerable") else "Non"],
    ]
    t = _kv_table(rows, [col_w * 0.4, col_w * 0.6])
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 21 — Directory Listing
# ---------------------------------------------------------------------------
def _build_dirlist_section(
    r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False
) -> list:
    story = []
    story += _section_header(21, "Directory Listing & Chemins sensibles", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-dirlist).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    findings = r.get("findings", [])
    if not findings:
        story.append(Paragraph("Aucun chemin sensible exposé.", styles["body"]))
        return story

    col_w = page_w - 4 * cm
    head_style = ParagraphStyle(
        "th21", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [
            Paragraph("Chemin", head_style),
            Paragraph("Catégorie", head_style),
            Paragraph("Sévérité", head_style),
            Paragraph("HTTP", head_style),
        ]
    ]
    for f in findings:
        rows.append([f["path"], f["category"], f["severity"], str(f["status_code"])])

    t = _kv_table(rows, [col_w * 0.38, col_w * 0.22, col_w * 0.22, col_w * 0.18])
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 22 — Robots & Sitemap
# ---------------------------------------------------------------------------
def _build_robots_section(
    r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False
) -> list:
    story = []
    story += _section_header(22, "Robots.txt & Sitemap", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-robots).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    col_w = page_w - 4 * cm
    sensitive = r.get("sensitive_disallowed", [])
    head_style = ParagraphStyle(
        "th22", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [Paragraph("Propriété", head_style), Paragraph("Valeur", head_style)],
        ["robots.txt", "Trouvé" if r.get("robots_found") else "Absent"],
        ["Disallow entries", str(len(r.get("disallowed_paths", [])))],
        ["Chemins sensibles", ", ".join(sensitive[:6]) if sensitive else "Aucun"],
        ["Sitemap", "Trouvé" if r.get("sitemap_found") else "Absent"],
        ["URLs sitemap", str(r.get("sitemap_url_count", 0))],
    ]
    t = _kv_table(rows, [col_w * 0.35, col_w * 0.65])
    story.append(t)
    return story


# ---------------------------------------------------------------------------
# Section 23 — JWT Security
# ---------------------------------------------------------------------------
def _build_jwt_section(
    r: dict[str, Any], styles: dict[str, Any], page_w: float, skipped: bool = False
) -> list:
    story = []
    story += _section_header(23, "Sécurité JWT", styles)

    if skipped:
        story.append(Paragraph("Module non exécuté (--skip-jwt).", styles["body"]))
        return story

    story.append(_status_inline(r.get("status", "OK")))
    story.append(Spacer(1, 0.3 * cm))

    col_w = page_w - 4 * cm
    analyses = r.get("analyses", [])
    if not analyses:
        story.append(
            Paragraph(
                f"Tokens détectés : {r.get('tokens_found', 0)} — Aucune vulnérabilité JWT exposée.",
                styles["body"],
            )
        )
        return story

    head_style = ParagraphStyle(
        "th23", fontName="Helvetica-Bold", fontSize=10, textColor=COLOR_PRIMARY
    )
    rows = [
        [
            Paragraph("Token (début)", head_style),
            Paragraph("Problèmes", head_style),
            Paragraph("Sévérité", head_style),
        ]
    ]
    for a in analyses:
        issues = ", ".join(a["issues"]) if a["issues"] else "OK"
        sev = a["severity"]
        sev_style = ParagraphStyle(
            "sv23",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=_status_color(
                sev if sev in ("OK", "WARNING", "CRITICAL") else "WARNING"
            ),
        )
        rows.append([a["token"][:40], issues, Paragraph(sev, sev_style)])

    t = _kv_table(rows, [col_w * 0.35, col_w * 0.45, col_w * 0.20])
    story.append(t)
    return story
