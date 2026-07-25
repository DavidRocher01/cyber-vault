"""
report_generator — PDF audit report generation (package).

Split from the former single-file ``report_generator.py`` into cohesive
submodules:
  * theme           — brand colours, paragraph styles, shared table/section helpers
  * doctemplate     — AuditDocTemplate (page frames + branded footer)
  * cover           — cover page, table of contents, executive summary
  * sections        — one builder per scan probe (ssl, headers, ports, sca, …)
  * recommendations — prioritised remediation recommendations
  * generator       — generate_report(): assemble every section into the PDF

Every name the previous module exposed is re-exported here so that
``from scanner.report_generator import generate_report, _build_ssl_section, ...``
and ``COLOR_CRITICAL`` / ``_build_styles`` continue to resolve unchanged.
"""

from .cover import _build_cover, _build_executive_summary, _build_toc
from .doctemplate import AuditDocTemplate
from .generator import generate_report
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
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CARD,
    COLOR_CRITICAL,
    COLOR_LIGHT_BORDER,
    COLOR_MUTED,
    COLOR_OK,
    COLOR_PRIMARY,
    COLOR_ROW_ALT,
    COLOR_TEXT,
    COLOR_WARNING,
    COLOR_WHITE,
    _build_styles,
    _kv_styles,
    _not_scanned_table,
    _section_header,
    _status_bullet,
    _status_color,
    _status_inline,
    _std_table_style,
)

__all__ = [
    "generate_report",
    "AuditDocTemplate",
    # theme
    "COLOR_CRITICAL",
    "COLOR_WARNING",
    "COLOR_OK",
    "COLOR_PRIMARY",
    "COLOR_BG",
    "COLOR_CARD",
    "COLOR_BORDER",
    "COLOR_MUTED",
    "COLOR_TEXT",
    "COLOR_WHITE",
    "COLOR_LIGHT_BORDER",
    "COLOR_ROW_ALT",
    "_build_styles",
    "_status_color",
    "_status_bullet",
    "_status_inline",
    "_std_table_style",
    "_section_header",
    "_kv_styles",
    "_not_scanned_table",
    # cover
    "_build_cover",
    "_build_toc",
    "_build_executive_summary",
    # recommendations
    "_build_recommendations",
    # sections
    "_build_ssl_section",
    "_build_headers_section",
    "_build_ports_section",
    "_build_sca_section",
    "_build_email_section",
    "_build_cookie_section",
    "_build_cors_section",
    "_build_ip_reputation_section",
    "_build_dns_section",
    "_build_cms_section",
    "_build_waf_section",
    "_build_breach_section",
    "_build_tech_section",
    "_build_tls_section",
    "_build_takeover_section",
    "_build_threat_intel_section",
    "_build_http_methods_section",
    "_build_open_redirect_section",
    "_build_clickjacking_section",
    "_build_dirlist_section",
    "_build_robots_section",
    "_build_jwt_section",
]
