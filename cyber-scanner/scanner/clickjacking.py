"""
Module H2 — Clickjacking Detection (Tier 4)
Checks X-Frame-Options and Content-Security-Policy frame-ancestors
to detect clickjacking vulnerability.
No API key required.
"""

import re
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8


def _fetch_headers(url: str) -> dict[str, str] | None:
    """Fetch HTTP response headers from url. Returns lowercased dict or None."""
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,
            allow_redirects=True,
        )
        return {k.lower(): v for k, v in resp.headers.items()}
    except requests.exceptions.RequestException:
        return None


def _check_xfo(headers: dict[str, str]) -> dict[str, Any]:
    """
    Analyse the X-Frame-Options header.
    Returns dict with present, value, and protected flag.
    """
    xfo = headers.get("x-frame-options", "")
    if not xfo:
        return {"present": False, "value": None, "protected": False}
    value = xfo.strip().upper()
    protected = value in ("DENY", "SAMEORIGIN")
    return {"present": True, "value": xfo, "protected": protected}


def _check_csp_frame_ancestors(headers: dict[str, str]) -> dict[str, Any]:
    """
    Analyse Content-Security-Policy for frame-ancestors directive.
    Returns dict with present, value, and protected flag.
    """
    csp = headers.get("content-security-policy", "")
    if not csp:
        return {"present": False, "value": None, "protected": False}

    match = re.search(r"frame-ancestors\s+([^;]+)", csp, re.IGNORECASE)
    if not match:
        return {"present": False, "value": None, "protected": False}

    directive = match.group(1).strip()
    # 'none' or 'self' are safe; wildcard '*' or missing = not protected
    protected = bool(re.search(r"(?:^|\s)'none'|(?:^|\s)'self'", directive, re.IGNORECASE))
    return {"present": True, "value": directive, "protected": protected}


def check_clickjacking(url: str) -> dict[str, Any]:
    """
    Check a URL for clickjacking vulnerability.

    Args:
        url: Full URL to check (e.g. "https://example.com")

    Returns:
        A dict with keys:
            vulnerable          — True if unprotected
            xfo                 — X-Frame-Options analysis
            csp_frame_ancestors — CSP frame-ancestors analysis
            status              — "OK" | "WARNING" | "CRITICAL"
            error               — error message or None
    """
    result: dict[str, Any] = {
        "vulnerable":          False,
        "xfo":                 {},
        "csp_frame_ancestors": {},
        "status":              "OK",
        "error":               None,
    }

    headers = _fetch_headers(url)
    if headers is None:
        result["error"]  = "Failed to fetch target URL"
        result["status"] = "CRITICAL"
        return result

    xfo  = _check_xfo(headers)
    csp  = _check_csp_frame_ancestors(headers)

    result["xfo"]                 = xfo
    result["csp_frame_ancestors"] = csp

    protected = xfo["protected"] or csp["protected"]
    result["vulnerable"] = not protected

    if result["vulnerable"]:
        result["status"] = "CRITICAL"
    elif xfo["present"] or csp["present"]:
        # Header present but not ideal config → warning
        result["status"] = "WARNING" if not (xfo["protected"] and csp["protected"]) else "OK"
    else:
        result["status"] = "CRITICAL"

    return result
