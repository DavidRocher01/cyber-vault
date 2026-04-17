"""
Module G1 — Technology Stack Fingerprinting (Tier 3)
Detects web server, frameworks, JS libraries, CDN, analytics, and CMS hints
from HTTP headers and HTML content. No API key required.
"""

import re
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 10

# ---------------------------------------------------------------------------
# Fingerprint signatures
# Each entry: {"category": str, "name": str, "type": "header"|"html"|"cookie",
#              "key": str (for header), "pattern": str}
# ---------------------------------------------------------------------------
SIGNATURES: list[dict[str, Any]] = [
    # --- Web servers ---
    {"category": "server",    "name": "nginx",         "type": "header", "key": "server",           "pattern": r"(?i)nginx"},
    {"category": "server",    "name": "Apache",        "type": "header", "key": "server",           "pattern": r"(?i)apache"},
    {"category": "server",    "name": "IIS",           "type": "header", "key": "server",           "pattern": r"(?i)microsoft-iis"},
    {"category": "server",    "name": "LiteSpeed",     "type": "header", "key": "server",           "pattern": r"(?i)litespeed"},
    {"category": "server",    "name": "Caddy",         "type": "header", "key": "server",           "pattern": r"(?i)caddy"},
    {"category": "server",    "name": "Cloudflare",    "type": "header", "key": "server",           "pattern": r"(?i)cloudflare"},
    # --- Backend frameworks / languages ---
    {"category": "framework", "name": "PHP",           "type": "header", "key": "x-powered-by",     "pattern": r"(?i)php"},
    {"category": "framework", "name": "ASP.NET",       "type": "header", "key": "x-powered-by",     "pattern": r"(?i)asp\.net"},
    {"category": "framework", "name": "Express",       "type": "header", "key": "x-powered-by",     "pattern": r"(?i)express"},
    {"category": "framework", "name": "Django",        "type": "header", "key": "x-frame-options",  "pattern": r"(?i)sameorigin"},
    {"category": "framework", "name": "Ruby on Rails", "type": "header", "key": "x-runtime",        "pattern": r"[\d.]+"},
    {"category": "framework", "name": "Laravel",       "type": "cookie", "pattern": r"laravel_session"},
    {"category": "framework", "name": "Django",        "type": "cookie", "pattern": r"csrftoken"},
    # --- JS frameworks ---
    {"category": "js",        "name": "React",         "type": "html",   "pattern": r"(?:react(?:\.min)?\.js|__react|data-reactroot|data-reactid)"},
    {"category": "js",        "name": "Vue.js",        "type": "html",   "pattern": r"(?:vue(?:\.min)?\.js|__vue__|data-v-)"},
    {"category": "js",        "name": "Angular",       "type": "html",   "pattern": r"(?:angular(?:\.min)?\.js|ng-version=|ng-app)"},
    {"category": "js",        "name": "jQuery",        "type": "html",   "pattern": r"jquery(?:\.min)?\.js"},
    {"category": "js",        "name": "Next.js",       "type": "html",   "pattern": r"(?:__NEXT_DATA__|/_next/static/)"},
    {"category": "js",        "name": "Nuxt.js",       "type": "html",   "pattern": r"(?:__nuxt|/_nuxt/)"},
    {"category": "js",        "name": "Svelte",        "type": "html",   "pattern": r"__svelte"},
    {"category": "js",        "name": "Bootstrap",     "type": "html",   "pattern": r"bootstrap(?:\.min)?\.(?:css|js)"},
    # --- CDN ---
    {"category": "cdn",       "name": "Cloudflare CDN","type": "header", "key": "cf-ray",           "pattern": r".+"},
    {"category": "cdn",       "name": "Fastly",        "type": "header", "key": "x-served-by",      "pattern": r"(?i)fastly"},
    {"category": "cdn",       "name": "Akamai",        "type": "header", "key": "x-check-cacheable", "pattern": r".+"},
    {"category": "cdn",       "name": "jsDelivr",      "type": "html",   "pattern": r"cdn\.jsdelivr\.net"},
    {"category": "cdn",       "name": "cdnjs",         "type": "html",   "pattern": r"cdnjs\.cloudflare\.com"},
    {"category": "cdn",       "name": "unpkg",         "type": "html",   "pattern": r"unpkg\.com"},
    # --- Analytics ---
    {"category": "analytics", "name": "Google Analytics", "type": "html", "pattern": r"(?:google-analytics\.com/analytics\.js|gtag\(|UA-\d+-\d+|G-[A-Z0-9]+)"},
    {"category": "analytics", "name": "Google Tag Manager","type": "html","pattern": r"googletagmanager\.com/gtm\.js"},
    {"category": "analytics", "name": "Matomo",        "type": "html",   "pattern": r"(?:matomo\.js|piwik\.js)"},
    {"category": "analytics", "name": "Hotjar",        "type": "html",   "pattern": r"static\.hotjar\.com"},
    {"category": "analytics", "name": "Segment",       "type": "html",   "pattern": r"cdn\.segment\.com"},
    # --- Security headers as tech signals ---
    {"category": "security",  "name": "HSTS",          "type": "header", "key": "strict-transport-security", "pattern": r".+"},
    {"category": "security",  "name": "CSP",           "type": "header", "key": "content-security-policy",   "pattern": r".+"},
]


def _fetch(url: str) -> dict[str, Any] | None:
    """Fetch a URL and return {headers, html, cookies} or None."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True)  # nosec B501 nosemgrep: python.requests.security.verify-disabled
        return {
            "headers": {k.lower(): v for k, v in resp.headers.items()},
            "html":    resp.text[:80_000],
            "cookies": "; ".join(resp.cookies.keys()),
        }
    except requests.exceptions.RequestException:
        return None


def _match_signature(sig: dict[str, Any], page: dict[str, Any]) -> bool:
    """Return True if a signature matches the fetched page."""
    t = sig["type"]
    if t == "html":
        return bool(re.search(sig["pattern"], page["html"], re.IGNORECASE))
    if t == "header":
        val = page["headers"].get(sig["key"])
        if not val:
            return False
        return bool(re.search(sig["pattern"], val, re.IGNORECASE))
    if t == "cookie":
        return bool(re.search(sig["pattern"], page["cookies"], re.IGNORECASE))
    return False


def _group_by_category(matches: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Group detected technology names by category."""
    grouped: dict[str, list[str]] = {}
    for m in matches:
        cat = m["category"]
        grouped.setdefault(cat, [])
        if m["name"] not in grouped[cat]:
            grouped[cat].append(m["name"])
    return grouped


def fingerprint_tech(url: str) -> dict[str, Any]:
    """
    Detect the technology stack of a web target.

    Args:
        url: Full URL to analyse (e.g. "https://example.com")

    Returns:
        A dict with keys:
            technologies  — dict[category, list[name]] of detected tech
            total         — total number of detected technologies
            status        — "OK" | "WARNING" | "CRITICAL"
            error         — error message or None
    """
    result: dict[str, Any] = {
        "technologies": {},
        "total": 0,
        "status": "OK",
        "error": None,
    }

    page = _fetch(url)
    if not page:
        result["error"] = "Failed to fetch target URL"
        result["status"] = "CRITICAL"
        return result

    matches = [sig for sig in SIGNATURES if _match_signature(sig, page)]
    grouped = _group_by_category(matches)

    result["technologies"] = grouped
    result["total"] = sum(len(v) for v in grouped.values())

    # Expose server version → WARNING; PHP/ASP.NET x-powered-by → WARNING
    server_header = page["headers"].get("server", "")
    powered_by    = page["headers"].get("x-powered-by", "")
    version_exposed = bool(
        re.search(r"[\d.]{3,}", server_header) or
        re.search(r"[\d.]{3,}", powered_by)
    )

    if version_exposed:
        result["status"] = "WARNING"
        result["error"]  = (
            f"Version disclosed in headers — "
            f"Server: '{server_header}' X-Powered-By: '{powered_by}'"
        )
    elif result["total"] > 0:
        result["status"] = "OK"

    return result
