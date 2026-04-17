"""
Module F4 — WAF Detection
Detects Web Application Firewalls by analysing response headers, cookies,
and server behaviour when sending a crafted malicious payload.
No external API key required.
"""

from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 10

# Known WAF signatures: header key → (pattern, waf_name)
WAF_HEADER_SIGNATURES: list[dict[str, str]] = [
    {"header": "server",               "pattern": "cloudflare",      "waf": "Cloudflare"},
    {"header": "cf-ray",               "pattern": ".*",              "waf": "Cloudflare"},
    {"header": "x-sucuri-id",          "pattern": ".*",              "waf": "Sucuri"},
    {"header": "x-sucuri-cache",       "pattern": ".*",              "waf": "Sucuri"},
    {"header": "x-firewall-protection","pattern": ".*",              "waf": "Generic Firewall"},
    {"header": "x-waf-event-info",     "pattern": ".*",              "waf": "Generic WAF"},
    {"header": "x-amz-cf-id",          "pattern": ".*",              "waf": "AWS CloudFront"},
    {"header": "x-amzn-requestid",     "pattern": ".*",              "waf": "AWS WAF"},
    {"header": "x-cdn",                "pattern": "incapsula",       "waf": "Imperva Incapsula"},
    {"header": "x-iinfo",              "pattern": ".*",              "waf": "Imperva Incapsula"},
    {"header": "x-powered-by",         "pattern": "(?i)imperva",     "waf": "Imperva"},
    {"header": "server",               "pattern": "(?i)akamai",      "waf": "Akamai"},
    {"header": "x-check-cacheable",    "pattern": ".*",              "waf": "Akamai"},
    {"header": "server",               "pattern": "(?i)barracuda",   "waf": "Barracuda"},
    {"header": "x-aesgws",             "pattern": ".*",              "waf": "ModSecurity/AESGWS"},
    {"header": "x-denied-reason",      "pattern": ".*",              "waf": "ModSecurity"},
    {"header": "x-bizsec",             "pattern": ".*",              "waf": "BizSec WAF"},
    {"header": "x-f5-dpi",             "pattern": ".*",              "waf": "F5 BIG-IP ASM"},
    {"header": "x-datadome-cid",       "pattern": ".*",              "waf": "DataDome Bot Protection"},
]

WAF_COOKIE_SIGNATURES: list[dict[str, str]] = [
    {"pattern": "^__cfduid",      "waf": "Cloudflare"},
    {"pattern": "^cf_clearance",  "waf": "Cloudflare"},
    {"pattern": "^incap_ses",     "waf": "Imperva Incapsula"},
    {"pattern": "^visid_incap",   "waf": "Imperva Incapsula"},
    {"pattern": "^sucuri_cloudp", "waf": "Sucuri"},
    {"pattern": "^ak_bmsc",       "waf": "Akamai Bot Manager"},
    {"pattern": "^bm_sz",         "waf": "Akamai Bot Manager"},
    {"pattern": "^DataDome",      "waf": "DataDome"},
]

# Payload that should trigger WAF if present
WAF_TEST_PAYLOAD = "/?q=<script>alert(1)</script>&id=1+OR+1=1--"


def _probe(url: str, path: str = "") -> dict[str, Any] | None:
    """Fetch url+path and return normalised response dict."""
    try:
        resp = requests.get(
            url.rstrip("/") + path,
            timeout=REQUEST_TIMEOUT,
            verify=False,  # nosec B501 nosemgrep: python.requests.security.verify-disabled
            allow_redirects=True,
        )
        return {
            "headers": {k.lower(): v for k, v in resp.headers.items()},
            "cookies": [c.name for c in resp.cookies],
            "status_code": resp.status_code,
        }
    except requests.exceptions.RequestException:
        return None


def _detect_from_response(probe: dict[str, Any]) -> str | None:
    """Return WAF name if found in headers or cookies, else None."""
    import re

    headers = probe["headers"]
    cookies = probe["cookies"]

    for sig in WAF_HEADER_SIGNATURES:
        val = headers.get(sig["header"], "")
        if val and re.search(sig["pattern"], val, re.IGNORECASE):
            return sig["waf"]

    for sig in WAF_COOKIE_SIGNATURES:
        for cookie in cookies:
            if re.match(sig["pattern"], cookie, re.IGNORECASE):
                return sig["waf"]

    return None


def detect_waf(url: str) -> dict[str, Any]:
    """
    Attempt to detect a WAF protecting the target URL.

    Strategy:
    1. Normal request — check headers/cookies for WAF signatures.
    2. Malicious payload — if normal request doesn't reveal WAF, check
       whether a crafted XSS+SQLi payload triggers a block (403/406/429).

    Args:
        url: Full URL to probe (e.g. "https://example.com")

    Returns:
        A dict with keys:
            detected        — True if a WAF was identified
            waf_name        — Name of the WAF or "Unknown WAF" if blocked but unidentified
            method          — "header_signature" | "payload_block" | None
            block_status    — HTTP status code from the payload probe (or None)
            status          — "OK" | "WARNING"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "detected": False,
        "waf_name": None,
        "method": None,
        "block_status": None,
        "status": "OK",
        "error": None,
    }

    # Probe 1: normal request
    normal = _probe(url)
    if not normal:
        result["error"] = "Failed to connect to target"
        result["status"] = "WARNING"
        return result

    waf = _detect_from_response(normal)
    if waf:
        result["detected"] = True
        result["waf_name"] = waf
        result["method"] = "header_signature"
        result["status"] = "WARNING"
        return result

    # Probe 2: malicious payload
    payload_probe = _probe(url, WAF_TEST_PAYLOAD)
    if payload_probe and payload_probe["status_code"] in (403, 406, 429, 503):
        # Check headers/cookies again on the blocked response
        waf = _detect_from_response(payload_probe)
        result["detected"] = True
        result["waf_name"] = waf or "Unknown WAF"
        result["method"] = "payload_block"
        result["block_status"] = payload_probe["status_code"]
        result["status"] = "WARNING"
    else:
        result["detected"] = False
        result["waf_name"] = None
        result["status"] = "OK"

    return result
