"""
Module G4 — Threat Intelligence (Tier 3)
Queries Shodan InternetDB (free, no API key) for open ports, CVEs, tags
and hostnames associated with an IP address.
Optional: AbuseIPDB (requires free API key) for abuse confidence score.
"""

import socket
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 10
SHODAN_INTERNETDB = "https://internetdb.shodan.io/{ip}"
ABUSEIPDB_URL     = "https://api.abuseipdb.com/api/v2/check"


def _resolve_ip(hostname: str) -> str | None:
    """Resolve hostname to its primary IPv4 address."""
    try:
        return socket.gethostbyname(hostname)
    except socket.gaierror:
        return None


def _query_shodan(ip: str) -> dict[str, Any] | None:
    """
    Query Shodan InternetDB for a given IP.
    Returns raw JSON dict or None on error.
    """
    try:
        resp = requests.get(
            SHODAN_INTERNETDB.format(ip=ip),
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            return {}     # IP not indexed — clean
        return None
    except requests.exceptions.RequestException:
        return None


def _query_abuseipdb(ip: str, api_key: str) -> dict[str, Any] | None:
    """
    Query AbuseIPDB for abuse confidence score.
    Returns raw JSON dict or None on error.
    """
    try:
        resp = requests.get(
            ABUSEIPDB_URL,
            headers={"Key": api_key, "Accept": "application/json"},
            params={"ipAddress": ip, "maxAgeInDays": 90},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            return resp.json().get("data", {})
        return None
    except requests.exceptions.RequestException:
        return None


def get_threat_intel(hostname: str, abuseipdb_key: str | None = None) -> dict[str, Any]:
    """
    Retrieve threat intelligence for a hostname.

    Args:
        hostname:       Target hostname (e.g. "example.com")
        abuseipdb_key:  Optional AbuseIPDB API key for abuse score.

    Returns:
        A dict with keys:
            ip              — resolved IP address or None
            open_ports      — list of open ports from Shodan
            cves            — list of CVE IDs from Shodan
            tags            — list of Shodan tags (e.g. "cloud", "honeypot")
            hostnames       — other hostnames sharing this IP (Shodan)
            abuse_score     — AbuseIPDB confidence score (0-100) or None
            abuse_reports   — number of abuse reports or None
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "ip":            None,
        "open_ports":    [],
        "cves":          [],
        "tags":          [],
        "hostnames":     [],
        "abuse_score":   None,
        "abuse_reports": None,
        "status":        "OK",
        "error":         None,
    }

    ip = _resolve_ip(hostname)
    if not ip:
        result["error"]  = f"Could not resolve hostname: {hostname}"
        result["status"] = "CRITICAL"
        return result

    result["ip"] = ip

    # --- Shodan InternetDB ---
    shodan_data = _query_shodan(ip)
    if shodan_data is None:
        result["error"] = "Shodan InternetDB unreachable"
        result["status"] = "WARNING"
    elif shodan_data:
        result["open_ports"] = shodan_data.get("ports", [])
        result["cves"]       = shodan_data.get("vulns", [])
        result["tags"]       = shodan_data.get("tags", [])
        result["hostnames"]  = shodan_data.get("hostnames", [])

    # --- AbuseIPDB (optional) ---
    if abuseipdb_key:
        abuse_data = _query_abuseipdb(ip, abuseipdb_key)
        if abuse_data:
            result["abuse_score"]   = abuse_data.get("abuseConfidenceScore")
            result["abuse_reports"] = abuse_data.get("totalReports")

    # --- Determine status ---
    issues = []
    if result["cves"]:
        issues.append("cves")
    if result["abuse_score"] is not None and result["abuse_score"] >= 25:
        issues.append("abuse")
    if "honeypot" in result["tags"]:
        issues.append("honeypot")

    if "cves" in issues or "abuse" in issues:
        result["status"] = "CRITICAL"
    elif issues or len(result["open_ports"]) > 5:
        result["status"] = "WARNING"

    return result
