"""
Module F2 — CMS Detection
Detects the CMS (WordPress, Drupal, Joomla, etc.) and version from
HTTP headers, HTML meta tags, cookies, and URL fingerprints.
No external API key required.
"""

import re
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 10

# CMS fingerprint signatures
CMS_SIGNATURES: list[dict[str, Any]] = [
    {
        "name": "WordPress",
        "checks": [
            {"type": "url_path",   "value": "/wp-login.php"},
            {"type": "url_path",   "value": "/wp-content/"},
            {"type": "html",       "pattern": r'content=["\']WordPress'},
            {"type": "header",     "key": "x-powered-by", "pattern": r"(?i)wordpress"},
            {"type": "cookie",     "pattern": r"wordpress_"},
        ],
        "version_patterns": [
            {"type": "html",   "pattern": r'content=["\']WordPress ([\d.]+)'},
            {"type": "url_path", "value": "/feed/", "pattern": r"<generator>.*WordPress ([\d.]+)</generator>"},
        ],
    },
    {
        "name": "Drupal",
        "checks": [
            {"type": "header",   "key": "x-generator",   "pattern": r"(?i)drupal"},
            {"type": "header",   "key": "x-drupal-cache", "pattern": r".*"},
            {"type": "html",     "pattern": r'content=["\']Drupal'},
            {"type": "url_path", "value": "/sites/default/"},
        ],
        "version_patterns": [
            {"type": "html", "pattern": r'content=["\']Drupal ([\d.]+)'},
        ],
    },
    {
        "name": "Joomla",
        "checks": [
            {"type": "url_path", "value": "/administrator/"},
            {"type": "html",     "pattern": r'content=["\']Joomla'},
            {"type": "cookie",   "pattern": r"joomla_"},
        ],
        "version_patterns": [
            {"type": "html", "pattern": r'content=["\']Joomla! ([\d.]+)'},
        ],
    },
    {
        "name": "Shopify",
        "checks": [
            {"type": "header", "key": "x-shopify-stage", "pattern": r".*"},
            {"type": "html",   "pattern": r'cdn\.shopify\.com'},
            {"type": "cookie", "pattern": r"_shopify_"},
        ],
        "version_patterns": [],
    },
    {
        "name": "Wix",
        "checks": [
            {"type": "html", "pattern": r'static\.wixstatic\.com'},
            {"type": "html", "pattern": r'X-Wix-Published-Version'},
        ],
        "version_patterns": [],
    },
    {
        "name": "Squarespace",
        "checks": [
            {"type": "header", "key": "server", "pattern": r"(?i)squarespace"},
            {"type": "html",   "pattern": r'squarespace\.com/universal'},
        ],
        "version_patterns": [],
    },
]


def _fetch(url: str) -> dict[str, Any] | None:
    """Fetch a URL and return {headers, html, cookies, status_code} or None."""
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True)
        return {
            "headers": {k.lower(): v for k, v in resp.headers.items()},
            "html": resp.text[:50_000],
            "cookies": "; ".join(resp.cookies.keys()),
            "status_code": resp.status_code,
        }
    except requests.exceptions.RequestException:
        return None


def _check_signature(check: dict[str, Any], base_url: str, page: dict[str, Any]) -> bool:
    """Return True if a single CMS check matches."""
    check_type = check["type"]

    if check_type == "html":
        return bool(re.search(check["pattern"], page["html"], re.IGNORECASE))

    if check_type == "header":
        header_val = page["headers"].get(check["key"])
        if not header_val:
            return False
        return bool(re.search(check["pattern"], header_val, re.IGNORECASE))

    if check_type == "cookie":
        return bool(re.search(check["pattern"], page["cookies"], re.IGNORECASE))

    if check_type == "url_path":
        probe = _fetch(base_url.rstrip("/") + check["value"])
        return probe is not None and probe["status_code"] < 404

    return False


def _extract_version(version_patterns: list[dict], base_url: str, page: dict[str, Any]) -> str | None:
    """Try to extract CMS version from HTML or a secondary URL."""
    for vp in version_patterns:
        if vp["type"] == "html":
            m = re.search(vp["pattern"], page["html"], re.IGNORECASE)
            if m:
                return m.group(1)
        elif vp["type"] == "url_path":
            probe = _fetch(base_url.rstrip("/") + vp["value"])
            if probe:
                m = re.search(vp["pattern"], probe["html"], re.IGNORECASE)
                if m:
                    return m.group(1)
    return None


def detect_cms(url: str) -> dict[str, Any]:
    """
    Detect the CMS used by the target URL.

    Args:
        url: Full URL to analyse (e.g. "https://example.com")

    Returns:
        A dict with keys:
            cms             — detected CMS name or "Unknown"
            version         — version string or None
            confidence      — number of matching signatures
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "cms": "Unknown",
        "version": None,
        "confidence": 0,
        "status": "OK",
        "error": None,
    }

    page = _fetch(url)
    if not page:
        result["error"] = "Failed to fetch target URL"
        result["status"] = "CRITICAL"
        return result

    best_cms: str = "Unknown"
    best_score: int = 0
    best_version: str | None = None

    for sig in CMS_SIGNATURES:
        score = sum(
            1 for check in sig["checks"]
            if _check_signature(check, url, page)
        )
        if score > best_score:
            best_score = score
            best_cms = sig["name"]
            if score >= 1:
                best_version = _extract_version(sig["version_patterns"], url, page)

    result["cms"] = best_cms
    result["version"] = best_version
    result["confidence"] = best_score

    # Detecting a CMS is a WARNING — version exposure is CRITICAL
    if best_cms != "Unknown" and best_version:
        result["status"] = "CRITICAL"
    elif best_cms != "Unknown":
        result["status"] = "WARNING"
    else:
        result["status"] = "OK"

    return result
