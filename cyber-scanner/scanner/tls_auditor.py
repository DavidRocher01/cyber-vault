"""
Module G2 — Deep TLS Auditor (Tier 3)
Probes supported TLS protocol versions and cipher suites, checks HSTS
preload status, and validates certificate chain details.
Uses stdlib ssl + socket only — no external API key required.
"""

import socket
import ssl
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 10

# Protocols to probe (name → ssl constant)
PROTOCOL_PROBES: list[tuple[str, int]] = [
    ("TLSv1.0", ssl.PROTOCOL_TLS_CLIENT),
    ("TLSv1.1", ssl.PROTOCOL_TLS_CLIENT),
    ("TLSv1.2", ssl.PROTOCOL_TLS_CLIENT),
    ("TLSv1.3", ssl.PROTOCOL_TLS_CLIENT),
]

# Weak cipher patterns
WEAK_CIPHER_PATTERNS = [
    "RC4", "DES", "3DES", "NULL", "EXPORT", "ANON", "MD5",
    "CBC",  # CBC-mode ciphers are vulnerable to BEAST/POODLE
]


def _get_supported_protocols(hostname: str, port: int = 443) -> list[str]:
    """
    Return the list of TLS protocol versions accepted by the server.
    Uses minimum_version / maximum_version to force a specific version.
    """
    supported = []

    version_map = {
        "TLSv1.0": ssl.TLSVersion.TLSv1,  # nosec B502 — intentional: testing if target supports deprecated TLS
        "TLSv1.1": ssl.TLSVersion.TLSv1_1,  # nosec B502 — intentional: testing if target supports deprecated TLS
        "TLSv1.2": ssl.TLSVersion.TLSv1_2,
        "TLSv1.3": ssl.TLSVersion.TLSv1_3,
    }

    for version_name, tls_version in version_map.items():
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            ctx.minimum_version = tls_version
            ctx.maximum_version = tls_version
            with socket.create_connection((hostname, port), timeout=5) as sock:
                with ctx.wrap_socket(sock, server_hostname=hostname):
                    supported.append(version_name)
        except (ssl.SSLError, OSError, AttributeError):
            pass

    return supported


def _get_certificate_details(hostname: str, port: int = 443) -> dict[str, Any] | None:
    """Return subject, issuer, SANs from the server certificate."""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                cert = tls_sock.getpeercert()
                if not cert:
                    return None
                subject = dict(x[0] for x in cert.get("subject", []))
                issuer  = dict(x[0] for x in cert.get("issuer", []))
                sans    = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
                return {
                    "subject": subject.get("commonName", ""),
                    "issuer":  issuer.get("organizationName", ""),
                    "sans":    sans,
                    "not_after": cert.get("notAfter", ""),
                }
    except (ssl.SSLError, OSError):
        return None


def _check_hsts(hostname: str) -> dict[str, Any]:
    """Check HSTS header presence, max-age and preload flag."""
    result = {"present": False, "max_age": 0, "preload": False, "include_subdomains": False}
    try:
        resp = requests.get(
            f"https://{hostname}",
            timeout=REQUEST_TIMEOUT,
            verify=False,  # nosec B501 nosemgrep: python.requests.security.verify-disabled
            allow_redirects=True,
        )
        hsts = resp.headers.get("Strict-Transport-Security", "")
        if hsts:
            result["present"] = True
            ma = __import__("re").search(r"max-age=(\d+)", hsts)
            result["max_age"] = int(ma.group(1)) if ma else 0
            result["preload"] = "preload" in hsts.lower()
            result["include_subdomains"] = "includesubdomains" in hsts.lower()
    except requests.exceptions.RequestException:
        pass
    return result


def _find_weak_ciphers(hostname: str, port: int = 443) -> list[str]:
    """Return list of weak cipher suite names accepted by the server."""
    weak: list[str] = []
    try:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((hostname, port), timeout=5) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as tls_sock:
                cipher_name, _, _ = tls_sock.cipher()
                if any(p in cipher_name.upper() for p in WEAK_CIPHER_PATTERNS):
                    weak.append(cipher_name)
    except (ssl.SSLError, OSError):
        pass
    return weak


def audit_tls(hostname: str, port: int = 443) -> dict[str, Any]:
    """
    Perform a deep TLS audit on the target hostname.

    Args:
        hostname: Target hostname (e.g. "example.com")
        port:     TLS port (default 443)

    Returns:
        A dict with keys:
            supported_protocols  — list of accepted TLS versions
            weak_protocols       — TLS < 1.2 found
            certificate          — cert details dict or None
            hsts                 — HSTS details dict
            weak_ciphers         — list of weak cipher names detected
            status               — "OK" | "WARNING" | "CRITICAL"
            error                — error message or None
    """
    result: dict[str, Any] = {
        "supported_protocols": [],
        "weak_protocols":      [],
        "certificate":         None,
        "hsts":                {},
        "weak_ciphers":        [],
        "status":              "OK",
        "error":               None,
    }

    try:
        protocols = _get_supported_protocols(hostname, port)
        result["supported_protocols"] = protocols
        result["weak_protocols"] = [p for p in protocols if p in ("TLSv1.0", "TLSv1.1")]

        result["certificate"] = _get_certificate_details(hostname, port)
        result["hsts"]        = _check_hsts(hostname)
        result["weak_ciphers"] = _find_weak_ciphers(hostname, port)

    except Exception as exc:
        result["error"]  = str(exc)
        result["status"] = "CRITICAL"
        return result

    # Determine status
    issues = []
    if result["weak_protocols"]:
        issues.append("weak_protocols")
    if result["weak_ciphers"]:
        issues.append("weak_ciphers")
    if not result["hsts"].get("present"):
        issues.append("no_hsts")

    if "weak_protocols" in issues or "weak_ciphers" in issues:
        result["status"] = "CRITICAL"
    elif issues:
        result["status"] = "WARNING"
    else:
        result["status"] = "OK"

    return result
