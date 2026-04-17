"""
Module H1 — Open Redirect Detection (Tier 4)
Tests common redirect parameters for open redirect vulnerabilities.
No API key required.
"""

import re
from typing import Any
from urllib.parse import urlencode, urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8

# Common redirect parameter names
REDIRECT_PARAMS = [
    "redirect", "redirect_to", "redirect_url", "redirectTo", "redirectUrl",
    "url", "next", "next_url", "return", "return_url", "returnTo", "returnUrl",
    "goto", "go", "target", "dest", "destination", "redir", "r", "u",
    "forward", "location", "continue", "ref",
]

# Payloads to inject
PAYLOADS = [
    "https://evil-attacker.com",
    "//evil-attacker.com",
    "https://evil-attacker.com%2F%2F",
    "/\\evil-attacker.com",
]

EVIL_DOMAIN = "evil-attacker.com"


def _probe_redirect(url: str, param: str, payload: str) -> dict[str, Any]:
    """
    Send a GET request with a redirect parameter set to the payload.
    Returns probe result dict.
    """
    try:
        test_url = f"{url}?{urlencode({param: payload})}"
        resp = requests.get(
            test_url,
            timeout=REQUEST_TIMEOUT,
            verify=False,  # nosec B501 nosemgrep: python.requests.security.verify-disabled
            allow_redirects=False,
        )
        location = resp.headers.get("Location", "")
        redirected = bool(
            resp.status_code in (301, 302, 303, 307, 308) and
            EVIL_DOMAIN in location
        )
        return {
            "param":       param,
            "payload":     payload,
            "status_code": resp.status_code,
            "location":    location,
            "vulnerable":  redirected,
        }
    except requests.exceptions.RequestException:
        return {
            "param":       param,
            "payload":     payload,
            "status_code": None,
            "location":    "",
            "vulnerable":  False,
        }


def _is_redirect_response(probe: dict[str, Any]) -> bool:
    """Return True if the probe response is a vulnerable redirect."""
    return probe["vulnerable"]


def check_open_redirect(url: str) -> dict[str, Any]:
    """
    Test a URL for open redirect vulnerabilities.

    Args:
        url: Full URL to probe (e.g. "https://example.com")

    Returns:
        A dict with keys:
            vulnerable      — True if any redirect was exploitable
            findings        — list of vulnerable probe results
            tested          — total number of probes sent
            status          — "OK" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "vulnerable": False,
        "findings":   [],
        "tested":     0,
        "status":     "OK",
        "error":      None,
    }

    findings = []
    tested = 0

    for param in REDIRECT_PARAMS:
        for payload in PAYLOADS:
            probe = _probe_redirect(url, param, payload)
            tested += 1
            if _is_redirect_response(probe):
                findings.append(probe)
                break  # one payload confirmed — move to next param

    result["tested"]   = tested
    result["findings"] = findings
    result["vulnerable"] = len(findings) > 0

    if result["vulnerable"]:
        result["status"] = "CRITICAL"

    return result
