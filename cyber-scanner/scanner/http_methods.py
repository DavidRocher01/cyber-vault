"""
Module G5 — Dangerous HTTP Methods Detection (Tier 3)
Probes a URL for unsafe HTTP methods: PUT, DELETE, TRACE, CONNECT, OPTIONS.
A server accepting PUT/DELETE/TRACE is a direct security risk.
No API key required.
"""

from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8

# Methods and their risk level
METHOD_RISK: dict[str, str] = {
    "TRACE":   "CRITICAL",   # Enables XST (Cross-Site Tracing)
    "PUT":     "CRITICAL",   # File upload / arbitrary write
    "DELETE":  "CRITICAL",   # Resource deletion
    "CONNECT": "WARNING",    # Proxy tunnelling
    "OPTIONS": "INFO",       # Discloses allowed methods (not dangerous itself)
    "PATCH":   "WARNING",    # Partial update — may expose write access
}

DANGEROUS = {"TRACE", "PUT", "DELETE"}


def _probe_method(url: str, method: str) -> dict[str, Any]:
    """
    Send an HTTP request with the given method.
    Returns {method, status_code, allowed, error}.
    """
    try:
        resp = requests.request(
            method,
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,
            allow_redirects=False,
        )
        # A 2xx/3xx response or a non-405/501 means the method may be accepted
        allowed = resp.status_code not in (405, 501)
        return {
            "method":      method,
            "status_code": resp.status_code,
            "allowed":     allowed,
            "error":       None,
        }
    except requests.exceptions.RequestException as exc:
        return {
            "method":      method,
            "status_code": None,
            "allowed":     False,
            "error":       str(exc),
        }


def _parse_options(url: str) -> list[str]:
    """
    Send OPTIONS and parse the Allow header to get server-declared methods.
    Returns a list of method names.
    """
    try:
        resp = requests.options(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,
            allow_redirects=False,
        )
        allow_header = resp.headers.get("Allow", "")
        return [m.strip().upper() for m in allow_header.split(",") if m.strip()]
    except requests.exceptions.RequestException:
        return []


def check_http_methods(url: str) -> dict[str, Any]:
    """
    Probe a URL for dangerous HTTP methods.

    Args:
        url: Full URL to probe (e.g. "https://example.com")

    Returns:
        A dict with keys:
            allowed_methods     — list of methods that returned non-405/501
            dangerous_allowed   — list of CRITICAL methods accepted
            options_declared    — methods declared by OPTIONS Allow header
            probes              — list of per-method probe results
            status              — "OK" | "WARNING" | "CRITICAL"
            error               — error message or None
    """
    result: dict[str, Any] = {
        "allowed_methods":   [],
        "dangerous_allowed": [],
        "options_declared":  [],
        "probes":            [],
        "status":            "OK",
        "error":             None,
    }

    # Parse OPTIONS Allow header first
    result["options_declared"] = _parse_options(url)

    probes = []
    for method in METHOD_RISK:
        probe = _probe_method(url, method)
        probes.append(probe)
        if probe["allowed"]:
            result["allowed_methods"].append(method)
            if method in DANGEROUS:
                result["dangerous_allowed"].append(method)

    result["probes"] = probes

    if result["dangerous_allowed"]:
        result["status"] = "CRITICAL"
    elif any(m in result["allowed_methods"] for m in ("CONNECT", "PATCH")):
        result["status"] = "WARNING"

    return result
