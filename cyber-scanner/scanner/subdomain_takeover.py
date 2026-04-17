"""
Module G3 — Subdomain Takeover Detection (Tier 3)
For each discovered subdomain, checks whether its CNAME points to an
unclaimed external service (GitHub Pages, Heroku, Netlify, Shopify, etc.)
No API key required.
"""

import socket
from typing import Any

import requests
import urllib3

try:
    import dns.resolver
    DNS_AVAILABLE = True
except ImportError:
    DNS_AVAILABLE = False

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8

# ---------------------------------------------------------------------------
# Fingerprints for unclaimed-service detection
# key: CNAME suffix pattern → service name + body pattern that signals unclaimed
# ---------------------------------------------------------------------------
TAKEOVER_SIGNATURES: list[dict[str, Any]] = [
    {
        "service":  "GitHub Pages",
        "cname":    "github.io",
        "body":     r"There isn't a GitHub Pages site here",
    },
    {
        "service":  "Heroku",
        "cname":    "herokuapp.com",
        "body":     r"no such app",
    },
    {
        "service":  "Netlify",
        "cname":    "netlify.app",
        "body":     r"Not Found",
    },
    {
        "service":  "Shopify",
        "cname":    "myshopify.com",
        "body":     r"Sorry, this shop is currently unavailable",
    },
    {
        "service":  "Tumblr",
        "cname":    "tumblr.com",
        "body":     r"Whatever you were looking for doesn't currently exist",
    },
    {
        "service":  "Ghost",
        "cname":    "ghost.io",
        "body":     r"The thing you were looking for is no longer here",
    },
    {
        "service":  "Zendesk",
        "cname":    "zendesk.com",
        "body":     r"Help Center Closed",
    },
    {
        "service":  "Surge.sh",
        "cname":    "surge.sh",
        "body":     r"project not found",
    },
    {
        "service":  "Fastly",
        "cname":    "fastly.net",
        "body":     r"Fastly error: unknown domain",
    },
    {
        "service":  "AWS S3",
        "cname":    "s3.amazonaws.com",
        "body":     r"NoSuchBucket",
    },
    {
        "service":  "Azure",
        "cname":    "azurewebsites.net",
        "body":     r"404 Web Site not found",
    },
]


def _resolve_cname(hostname: str) -> str | None:
    """Resolve the CNAME of a hostname, return the target or None."""
    if not DNS_AVAILABLE:
        return None
    try:
        answers = dns.resolver.resolve(hostname, "CNAME")
        return str(answers[0].target).rstrip(".")
    except Exception:
        return None


def _resolve_a(hostname: str) -> str | None:
    """Resolve hostname to IP, return IP string or None."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def _fetch_body(hostname: str) -> str | None:
    """HTTP GET on the hostname, return response body or None."""
    for scheme in ("https", "http"):
        try:
            resp = requests.get(
                f"{scheme}://{hostname}",
                timeout=REQUEST_TIMEOUT,
                verify=False,  # nosec B501 nosemgrep: python.requests.security.verify-disabled
                allow_redirects=True,
            )
            return resp.text[:20_000]
        except requests.exceptions.RequestException:
            continue
    return None


def _check_takeover(hostname: str) -> dict[str, Any] | None:
    """
    Check a single hostname for takeover vulnerability.
    Returns a finding dict if vulnerable, else None.
    """
    import re

    cname = _resolve_cname(hostname)
    ip    = _resolve_a(hostname)

    # If NXDOMAIN (no IP), subdomain is dangling — high risk
    if ip is None:
        return {
            "subdomain": hostname,
            "cname":     cname,
            "service":   "Unknown",
            "reason":    "NXDOMAIN — dangling DNS entry",
            "severity":  "CRITICAL",
        }

    target = cname or hostname

    for sig in TAKEOVER_SIGNATURES:
        if sig["cname"] in target:
            body = _fetch_body(hostname)
            if body and re.search(sig["body"], body, re.IGNORECASE):
                return {
                    "subdomain": hostname,
                    "cname":     cname,
                    "service":   sig["service"],
                    "reason":    f"Unclaimed {sig['service']} resource",
                    "severity":  "CRITICAL",
                }

    return None


def check_subdomain_takeover(subdomains: list[str]) -> dict[str, Any]:
    """
    Check a list of subdomains for takeover vulnerabilities.

    Args:
        subdomains: List of fully-qualified hostnames to check.

    Returns:
        A dict with keys:
            vulnerable      — list of takeover findings
            total_checked   — number of subdomains checked
            total_vulnerable— number of vulnerable subdomains
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "vulnerable":       [],
        "total_checked":    0,
        "total_vulnerable": 0,
        "status":           "OK",
        "error":            None,
    }

    if not subdomains:
        result["error"] = "No subdomains provided — run DNS scan first"
        result["status"] = "WARNING"
        return result

    result["total_checked"] = len(subdomains)

    for hostname in subdomains:
        finding = _check_takeover(hostname)
        if finding:
            result["vulnerable"].append(finding)

    result["total_vulnerable"] = len(result["vulnerable"])

    if result["total_vulnerable"] > 0:
        result["status"] = "CRITICAL"

    return result
