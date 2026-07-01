"""
Module E4 — IP Reputation
Resolves the target hostname to an IP address and queries DNS-based
blacklists (DNSBL) to detect if the IP is flagged for abuse/spam/malware.
No API key required.
"""

import ipaddress
import socket
from typing import Any

import dns.resolver
import dns.exception
import dns.reversename

# Well-known DNSBL providers and what they flag
DNSBL_PROVIDERS: list[dict[str, str]] = [
    {"host": "zen.spamhaus.org",        "label": "Spamhaus ZEN",        "category": "spam/malware"},
    {"host": "bl.spamcop.net",          "label": "SpamCop",             "category": "spam"},
    {"host": "dnsbl.sorbs.net",         "label": "SORBS",               "category": "abuse"},
    {"host": "b.barracudacentral.org",  "label": "Barracuda",           "category": "spam"},
    {"host": "dnsbl-1.uceprotect.net",  "label": "UCEPROTECT L1",       "category": "spam"},
    {"host": "cbl.abuseat.org",         "label": "CBL Abuseat",         "category": "malware/botnet"},
]


# Substrings identifying a shared CDN / cloud edge in reverse-DNS (PTR) or CNAME.
# A blocklist hit on such an IP reflects the shared infrastructure — it is mutualised
# across thousands of sites — and does NOT reflect the reputation of the scanned site.
CDN_MARKERS: tuple[str, ...] = (
    "cloudfront",
    "cloudflare",
    "fastly",
    "akamai",
    "akamaiedge",
    "edgekey",
    "edgesuite",
    "amazonaws",
    "1e100",
    "googleusercontent",
    "azureedge",
    "azurefd",
    "incapdns",
    "stackpathdns",
    "cdn77",
    "bunnycdn",
)


def _reverse_ip(ip: str) -> str:
    """Return the reversed IP string for DNSBL lookup (e.g. 1.2.3.4 → 4.3.2.1)."""
    return ".".join(reversed(ip.split(".")))


def _detect_cdn(hostname: str, ip: str) -> str | None:
    """Return the CDN/cloud edge name if the IP or hostname belongs to a known shared
    CDN (via reverse-DNS PTR or CNAME), else None. Used to avoid flagging a site as
    CRITICAL just because its shared CDN edge IP is on a blocklist."""
    # 1. Reverse DNS (PTR) of the resolved IP — e.g. CloudFront -> *.r.cloudfront.net
    try:
        rev = dns.reversename.from_address(ip)
        for rdata in dns.resolver.resolve(rev, "PTR", lifetime=3):
            ptr = str(rdata).lower()
            for marker in CDN_MARKERS:
                if marker in ptr:
                    return marker
    except (dns.exception.DNSException, Exception):
        pass
    # 2. CNAME chain of the hostname (covers www.* pointing at a CDN)
    try:
        for rdata in dns.resolver.resolve(hostname, "CNAME", lifetime=3):
            target = str(rdata.target).lower()
            for marker in CDN_MARKERS:
                if marker in target:
                    return marker
    except (dns.exception.DNSException, Exception):
        pass
    return None


def _resolve_hostname(hostname: str) -> str | None:
    """Resolve hostname to IPv4 address, return None on failure."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def _query_dnsbl(reversed_ip: str, dnsbl_host: str) -> bool:
    """Return True if the IP is listed in the given DNSBL."""
    lookup = f"{reversed_ip}.{dnsbl_host}"
    try:
        dns.resolver.resolve(lookup, "A", lifetime=3)
        return True
    except (dns.exception.DNSException, Exception):
        return False


def check_ip_reputation(hostname: str) -> dict[str, Any]:
    """
    Check if the target IP is listed in DNS-based blacklists.

    Args:
        hostname: The hostname to resolve and check (e.g. "example.com")

    Returns:
        A dict with keys:
            ip              — resolved IP address
            listed_in       — list of {label, category} for each blacklist hit
            total_listed    — number of blacklists that flag the IP
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "ip": None,
        "cdn": None,
        "listed_in": [],
        "total_listed": 0,
        "status": "OK",
        "error": None,
    }

    ip = _resolve_hostname(hostname)
    if not ip:
        result["error"] = f"Could not resolve hostname: {hostname}"
        result["status"] = "CRITICAL"
        return result

    # Skip private/loopback addresses — no point checking those
    try:
        if ipaddress.ip_address(ip).is_private:
            result["ip"] = ip
            result["error"] = f"IP {ip} is private — DNSBL check skipped"
            result["status"] = "OK"
            return result
    except ValueError:
        pass

    result["ip"] = ip

    # A shared CDN edge IP (CloudFront, Cloudflare, …) is used by thousands of sites;
    # a DNSBL hit on it reflects the shared infrastructure, not this site. Don't flag
    # it CRITICAL — otherwise every site behind a CDN gets a false positive.
    cdn = _detect_cdn(hostname, ip)
    if cdn:
        result["cdn"] = cdn
        result["note"] = (
            f"IP appartenant à un CDN mutualisé ({cdn}) — sa réputation est partagée "
            "entre de nombreux sites et ne reflète pas le site scanné (blocklist non pertinente)."
        )
        result["status"] = "OK"
        return result

    reversed_ip = _reverse_ip(ip)
    listed_in: list[dict[str, str]] = []

    for provider in DNSBL_PROVIDERS:
        if _query_dnsbl(reversed_ip, provider["host"]):
            listed_in.append({"label": provider["label"], "category": provider["category"]})

    result["listed_in"] = listed_in
    result["total_listed"] = len(listed_in)

    if len(listed_in) >= 2:
        result["status"] = "CRITICAL"
    elif listed_in:
        result["status"] = "WARNING"
    else:
        result["status"] = "OK"

    return result
