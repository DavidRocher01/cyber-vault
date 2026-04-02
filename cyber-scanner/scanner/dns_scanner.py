"""
Module F1 — DNS & Subdomain Scanner
Enumerates subdomains via DNS resolution and attempts zone transfer (AXFR).
No external wordlist required — uses a built-in curated list.
"""

from typing import Any
import socket

import dns.resolver
import dns.zone
import dns.query
import dns.exception

# Curated subdomain wordlist covering the most common attack surface
SUBDOMAIN_WORDLIST: list[str] = [
    "www", "mail", "smtp", "pop", "imap", "ftp",
    "ns1", "ns2", "ns3", "dns", "dns1", "dns2",
    "api", "api2", "rest", "graphql",
    "admin", "administrator", "portal", "dashboard", "panel",
    "dev", "development", "test", "testing", "staging", "preprod", "uat",
    "blog", "shop", "store", "static", "assets", "cdn", "media", "images",
    "vpn", "remote", "ssh", "rdp", "bastion",
    "login", "auth", "sso", "oauth",
    "git", "gitlab", "github", "bitbucket", "ci", "jenkins",
    "jira", "confluence", "docs", "wiki",
    "monitor", "metrics", "grafana", "kibana", "elastic",
    "db", "database", "mysql", "postgres", "redis", "mongo",
    "backup", "old", "legacy", "beta", "v1", "v2",
]

RESOLVE_TIMEOUT = 3  # seconds per DNS query


def _resolve(hostname: str) -> str | None:
    """Try to resolve a hostname to an IPv4 address. Returns None on failure."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def _try_zone_transfer(domain: str) -> dict[str, Any]:
    """
    Attempt a DNS zone transfer (AXFR) against all NS records of the domain.
    Returns {vulnerable, nameservers, records_found}.
    """
    result: dict[str, Any] = {
        "vulnerable": False,
        "nameservers": [],
        "records_found": [],
    }
    try:
        ns_answers = dns.resolver.resolve(domain, "NS", lifetime=5)
        nameservers = [str(rdata.target).rstrip(".") for rdata in ns_answers]
        result["nameservers"] = nameservers
    except dns.exception.DNSException:
        return result

    for ns in nameservers:
        ns_ip = _resolve(ns)
        if not ns_ip:
            continue
        try:
            zone = dns.zone.from_xfr(dns.query.xfr(ns_ip, domain, timeout=5))
            names = [str(n) for n in zone.nodes.keys()]
            result["vulnerable"] = True
            result["records_found"] = names[:50]  # cap at 50
            break
        except Exception:
            continue

    return result


def scan_subdomains(domain: str) -> dict[str, Any]:
    """
    Enumerate subdomains by brute-forcing common names + attempting zone transfer.

    Args:
        domain: Base domain to scan (e.g. "example.com")

    Returns:
        A dict with keys:
            found           — list of {subdomain, ip} dicts
            total_found     — number of live subdomains discovered
            zone_transfer   — {vulnerable, nameservers, records_found}
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "found": [],
        "total_found": 0,
        "zone_transfer": {},
        "status": "OK",
        "error": None,
    }

    try:
        found: list[dict[str, str]] = []
        for sub in SUBDOMAIN_WORDLIST:
            hostname = f"{sub}.{domain}"
            ip = _resolve(hostname)
            if ip:
                found.append({"subdomain": hostname, "ip": ip})

        zone_transfer = _try_zone_transfer(domain)

        result["found"] = found
        result["total_found"] = len(found)
        result["zone_transfer"] = zone_transfer

        if zone_transfer["vulnerable"]:
            result["status"] = "CRITICAL"
        elif len(found) >= 5:
            result["status"] = "WARNING"
        else:
            result["status"] = "OK"

    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"
        result["status"] = "CRITICAL"

    return result
