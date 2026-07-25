"""generator.py — generate_report(): assemble every section into the final PDF."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm

from .cover import _build_cover, _build_executive_summary, _build_toc
from .doctemplate import AuditDocTemplate
from .recommendations import _build_recommendations
from .sections import (
    _build_breach_section,
    _build_clickjacking_section,
    _build_cms_section,
    _build_cookie_section,
    _build_cors_section,
    _build_dirlist_section,
    _build_dns_section,
    _build_email_section,
    _build_headers_section,
    _build_http_methods_section,
    _build_ip_reputation_section,
    _build_jwt_section,
    _build_open_redirect_section,
    _build_ports_section,
    _build_robots_section,
    _build_sca_section,
    _build_ssl_section,
    _build_takeover_section,
    _build_tech_section,
    _build_threat_intel_section,
    _build_tls_section,
    _build_waf_section,
)
from .theme import (
    _build_styles,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def generate_report(
    target_url: str,
    ssl_result: dict[str, Any],
    headers_result: dict[str, Any],
    port_result: dict[str, Any],
    output_path: str = "reports/rapport_audit.pdf",
    ports_skipped: bool = False,
    sca_result: dict[str, Any] | None = None,
    sca_skipped: bool = True,
    email_result: dict[str, Any] | None = None,
    email_skipped: bool = True,
    cookie_result: dict[str, Any] | None = None,
    cookie_skipped: bool = True,
    cors_result: dict[str, Any] | None = None,
    cors_skipped: bool = True,
    ip_result: dict[str, Any] | None = None,
    ip_skipped: bool = True,
    dns_result: dict[str, Any] | None = None,
    dns_skipped: bool = True,
    cms_result: dict[str, Any] | None = None,
    cms_skipped: bool = True,
    waf_result: dict[str, Any] | None = None,
    waf_skipped: bool = True,
    breach_result: dict[str, Any] | None = None,
    breach_skipped: bool = True,
    tech_result: dict[str, Any] | None = None,
    tech_skipped: bool = True,
    tls_result: dict[str, Any] | None = None,
    tls_skipped: bool = True,
    takeover_result: dict[str, Any] | None = None,
    takeover_skipped: bool = True,
    ti_result: dict[str, Any] | None = None,
    ti_skipped: bool = True,
    methods_result: dict[str, Any] | None = None,
    methods_skipped: bool = True,
    redirect_result: dict[str, Any] | None = None,
    redirect_skipped: bool = True,
    clickjacking_result: dict[str, Any] | None = None,
    clickjacking_skipped: bool = True,
    dirlist_result: dict[str, Any] | None = None,
    dirlist_skipped: bool = True,
    robots_result: dict[str, Any] | None = None,
    robots_skipped: bool = True,
    jwt_result: dict[str, Any] | None = None,
    jwt_skipped: bool = True,
) -> str:
    """
    Generate a professional PDF audit report.

    Args:
        target_url:     The scanned URL.
        ssl_result:     Dict returned by check_ssl().
        headers_result: Dict returned by check_headers().
        port_result:    Dict returned by scan_ports() or None/empty if skipped.
        output_path:    Destination file path (PDF).
        ports_skipped:  True when --skip-ports was used.
        sca_result:     Dict returned by check_sca() or None if skipped.
        sca_skipped:    True when SCA was not requested.

    Returns:
        The resolved output path where the PDF was written.
    """
    output_path = os.path.normpath(output_path)
    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True,
    )

    report_date = datetime.now().strftime("%d/%m/%Y à %H:%M")
    page_w, page_h = A4

    doc = AuditDocTemplate(
        output_path,
        report_date=report_date,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2.5 * cm,  # extra 0.5 cm for top band
        bottomMargin=2 * cm,
    )

    styles = _build_styles()

    # Registre unique des modules de scan : (cle_statut, resultat, skipped,
    # builder, statut_par_defaut). skipped=None => module toujours actif (ssl,
    # headers), rendu sans argument `skipped`. Ce registre est la SEULE source
    # de verite pour le calcul des statuts ET l'assemblage du rapport, evitant
    # les 3 structures paralleles a maintenir a la main.
    probes: list[tuple[str, dict | None, bool | None, Any, str]] = [
        ("ssl", ssl_result, None, _build_ssl_section, "CRITICAL"),
        ("headers", headers_result, None, _build_headers_section, "CRITICAL"),
        ("ports", port_result, ports_skipped, _build_ports_section, "OK"),
        ("sca", sca_result, sca_skipped, _build_sca_section, "OK"),
        ("email", email_result, email_skipped, _build_email_section, "OK"),
        ("cookies", cookie_result, cookie_skipped, _build_cookie_section, "OK"),
        ("cors", cors_result, cors_skipped, _build_cors_section, "OK"),
        ("ip_rep", ip_result, ip_skipped, _build_ip_reputation_section, "OK"),
        ("dns", dns_result, dns_skipped, _build_dns_section, "OK"),
        ("cms", cms_result, cms_skipped, _build_cms_section, "OK"),
        ("waf", waf_result, waf_skipped, _build_waf_section, "OK"),
        ("breach", breach_result, breach_skipped, _build_breach_section, "OK"),
        ("tech", tech_result, tech_skipped, _build_tech_section, "OK"),
        ("tls", tls_result, tls_skipped, _build_tls_section, "OK"),
        ("takeover", takeover_result, takeover_skipped, _build_takeover_section, "OK"),
        ("threat_intel", ti_result, ti_skipped, _build_threat_intel_section, "OK"),
        (
            "http_methods",
            methods_result,
            methods_skipped,
            _build_http_methods_section,
            "OK",
        ),
        (
            "open_redirect",
            redirect_result,
            redirect_skipped,
            _build_open_redirect_section,
            "OK",
        ),
        (
            "clickjacking",
            clickjacking_result,
            clickjacking_skipped,
            _build_clickjacking_section,
            "OK",
        ),
        ("dir_listing", dirlist_result, dirlist_skipped, _build_dirlist_section, "OK"),
        ("robots", robots_result, robots_skipped, _build_robots_section, "OK"),
        ("jwt", jwt_result, jwt_skipped, _build_jwt_section, "OK"),
    ]

    # Compute statuses for summary
    statuses: dict[str, str] = {}
    for status_key, result, skipped, _build_fn, default_status in probes:
        active = bool(result) if skipped is None else (not skipped and bool(result))
        if active:
            statuses[status_key] = result.get("status", default_status)

    all_status_values = list(statuses.values())
    if "CRITICAL" in all_status_values:
        overall = "CRITICAL"
    elif "WARNING" in all_status_values:
        overall = "WARNING"
    else:
        overall = "OK"

    usable_w = page_w - 4 * cm  # leftMargin + rightMargin = 4 cm

    section_w = usable_w + 4 * cm
    story: list = []
    story += _build_cover(
        target_url, report_date, styles, usable_w, page_h, overall_status=overall
    )
    story += _build_toc(styles)
    story += _build_executive_summary(overall, statuses, styles, section_w)
    for _status_key, result, skipped, build_fn, _default in probes:
        if skipped is None:
            story += build_fn(result or {}, styles, section_w)
        else:
            story += build_fn(result or {}, styles, section_w, skipped=skipped)
    story += _build_recommendations(
        ssl_result or {},
        headers_result or {},
        port_result or {},
        styles,
        section_w,
        ports_skipped=ports_skipped,
        sca_result=sca_result or {},
        sca_skipped=sca_skipped,
    )

    doc.build(story)
    return output_path
