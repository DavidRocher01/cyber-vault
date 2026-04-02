"""
Module E1 — Email Security
Checks SPF, DKIM, and DMARC DNS records for a domain.
Requires: dnspython
"""

from typing import Any

import dns.resolver
import dns.exception

# Common DKIM selectors used by major providers
DKIM_SELECTORS: list[str] = [
    "google", "default", "mail", "dkim",
    "selector1", "selector2", "k1", "s1", "s2",
]


def _query_txt(name: str) -> list[str]:
    """Return all TXT record strings for a DNS name, or [] on failure."""
    try:
        answers = dns.resolver.resolve(name, "TXT", lifetime=5)
        return [b.decode() for rdata in answers for b in rdata.strings]
    except (dns.exception.DNSException, Exception):
        return []


def _check_spf(domain: str) -> dict[str, Any]:
    """Look for a valid SPF record in the domain's TXT records."""
    records = _query_txt(domain)
    spf_records = [r for r in records if r.startswith("v=spf1")]
    if spf_records:
        record = spf_records[0]
        # Warn if policy is too permissive (~all or ?all instead of -all)
        if "-all" in record:
            return {"found": True, "record": record, "strict": True}
        return {"found": True, "record": record, "strict": False}
    return {"found": False, "record": None, "strict": False}


def _check_dkim(domain: str) -> dict[str, Any]:
    """Try common DKIM selectors and return the first one that resolves."""
    for selector in DKIM_SELECTORS:
        name = f"{selector}._domainkey.{domain}"
        records = _query_txt(name)
        if any("v=DKIM1" in r or "k=rsa" in r or "p=" in r for r in records):
            return {"found": True, "selector": selector}
    return {"found": False, "selector": None}


def _check_dmarc(domain: str) -> dict[str, Any]:
    """Look for a DMARC record at _dmarc.<domain>."""
    records = _query_txt(f"_dmarc.{domain}")
    dmarc_records = [r for r in records if r.startswith("v=DMARC1")]
    if dmarc_records:
        record = dmarc_records[0]
        # Extract policy
        policy = "none"
        for part in record.split(";"):
            part = part.strip()
            if part.startswith("p="):
                policy = part[2:].strip().lower()
                break
        return {"found": True, "record": record, "policy": policy}
    return {"found": False, "record": None, "policy": None}


def check_email_security(domain: str) -> dict[str, Any]:
    """
    Check SPF, DKIM, and DMARC configuration for a domain.

    Args:
        domain: The domain to check (e.g. "example.com")

    Returns:
        A dict with keys:
            spf     — {found, record, strict}
            dkim    — {found, selector}
            dmarc   — {found, record, policy}
            issues  — list of human-readable problems
            status  — "OK" | "WARNING" | "CRITICAL"
            error   — error message or None
    """
    result: dict[str, Any] = {
        "spf": {},
        "dkim": {},
        "dmarc": {},
        "issues": [],
        "status": "OK",
        "error": None,
    }

    try:
        spf = _check_spf(domain)
        dkim = _check_dkim(domain)
        dmarc = _check_dmarc(domain)

        result["spf"] = spf
        result["dkim"] = dkim
        result["dmarc"] = dmarc

        issues: list[str] = []

        if not spf["found"]:
            issues.append("SPF manquant — les emails peuvent être falsifiés")
        elif not spf["strict"]:
            issues.append("SPF non strict (~all) — préférer -all pour bloquer les expéditeurs non autorisés")

        if not dkim["found"]:
            issues.append("DKIM non détecté — intégrité des emails non vérifiée")

        if not dmarc["found"]:
            issues.append("DMARC manquant — aucune politique de rejet des emails frauduleux")
        elif dmarc["policy"] == "none":
            issues.append("DMARC en mode surveillance (p=none) — passer à p=quarantine ou p=reject")

        result["issues"] = issues

        critical_count = sum([
            not spf["found"],
            not dkim["found"],
            not dmarc["found"],
        ])
        if critical_count >= 2:
            result["status"] = "CRITICAL"
        elif issues:
            result["status"] = "WARNING"
        else:
            result["status"] = "OK"

    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"
        result["status"] = "CRITICAL"

    return result
