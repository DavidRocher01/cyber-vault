"""Dark web breach checking — multi-provider (LeakCheck free + HIBP fallback)."""

from __future__ import annotations

from typing import Any

import requests

LEAKCHECK_URL = "https://leakcheck.io/api/public"
HIBP_EMAIL_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
HIBP_DOMAIN_URL = "https://haveibeenpwned.com/api/v3/breacheddomain/{domain}"
HIBP_BREACHES_URL = "https://haveibeenpwned.com/api/v3/breaches"

_HEADERS = {"User-Agent": "Rocher Cybersécurité/2.0"}
_TIMEOUT = 10


# ── LeakCheck.io (free, no API key required) ──────────────────────────────────


def check_email_leakcheck(email: str) -> dict[str, Any]:
    """Check email via LeakCheck.io public API — no key required."""
    try:
        resp = requests.get(
            LEAKCHECK_URL,
            params={"check": email},
            headers=_HEADERS,
            timeout=_TIMEOUT,
        )
        if resp.status_code == 429:
            return {
                "email": email,
                "breaches": [],
                "total": 0,
                "status": "unknown",
                "error": "Rate limited — retry later",
                "provider": "leakcheck",
            }
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return {
                "email": email,
                "breaches": [],
                "total": 0,
                "status": "unknown",
                "error": data.get("error", "Unknown error"),
                "provider": "leakcheck",
            }
        found = data.get("found", 0)
        sources = data.get("sources", [])
        breaches = [
            {
                "name": s.get("name", "Unknown"),
                "domain": "",
                "breach_date": s.get("date", ""),
                "pwn_count": 0,
                "data_classes": [],
                "is_sensitive": False,
            }
            for s in sources
        ]
        status = "CRITICAL" if found >= 3 else ("WARNING" if found > 0 else "OK")
        return {
            "email": email,
            "breaches": breaches,
            "total": found,
            "status": status,
            "error": None,
            "provider": "leakcheck",
        }
    except requests.exceptions.RequestException as exc:
        return {
            "email": email,
            "breaches": [],
            "total": 0,
            "status": "unknown",
            "error": str(exc),
            "provider": "leakcheck",
        }


# ── HaveIBeenPwned v3 (paid key required) ────────────────────────────────────


def check_email_hibp(email: str, api_key: str) -> dict[str, Any]:
    """Check email via HIBP v3 — requires paid API key."""
    if not api_key:
        return {
            "email": email,
            "breaches": [],
            "total": 0,
            "status": "unknown",
            "error": "HIBP API key not configured",
            "provider": "hibp",
        }
    headers = {**_HEADERS, "hibp-api-key": api_key}
    try:
        resp = requests.get(
            HIBP_EMAIL_URL.format(email=email),
            headers=headers,
            timeout=_TIMEOUT,
            params={"truncateResponse": "false"},
        )
        if resp.status_code == 404:
            return {
                "email": email,
                "breaches": [],
                "total": 0,
                "status": "OK",
                "error": None,
                "provider": "hibp",
            }
        if resp.status_code == 401:
            return {
                "email": email,
                "breaches": [],
                "total": 0,
                "status": "unknown",
                "error": "Invalid HIBP API key",
                "provider": "hibp",
            }
        if resp.status_code == 429:
            return {
                "email": email,
                "breaches": [],
                "total": 0,
                "status": "unknown",
                "error": "Rate limited — retry later",
                "provider": "hibp",
            }
        resp.raise_for_status()
        raw = resp.json()
        breaches = [
            {
                "name": b["Name"],
                "domain": b.get("Domain", ""),
                "breach_date": b.get("BreachDate", ""),
                "pwn_count": b.get("PwnCount", 0),
                "data_classes": b.get("DataClasses", []),
                "is_sensitive": b.get("IsSensitive", False),
            }
            for b in raw
        ]
        total = len(breaches)
        status = "CRITICAL" if total >= 3 else ("WARNING" if total > 0 else "OK")
        return {
            "email": email,
            "breaches": breaches,
            "total": total,
            "status": status,
            "error": None,
            "provider": "hibp",
        }
    except requests.exceptions.RequestException as exc:
        return {
            "email": email,
            "breaches": [],
            "total": 0,
            "status": "unknown",
            "error": str(exc),
            "provider": "hibp",
        }


# ── Unified entry point ───────────────────────────────────────────────────────


def check_email_breaches(email: str, api_key: str = "") -> dict[str, Any]:
    """Check email — uses HIBP if key available, falls back to LeakCheck."""
    if api_key:
        result = check_email_hibp(email, api_key)
        if result["status"] != "unknown":
            return result
    return check_email_leakcheck(email)


# ── HIBP breach catalog (free, no key required) ───────────────────────────────


def fetch_hibp_breach_catalog() -> list[dict]:
    """Fetch the full HIBP breach catalog metadata — no key needed."""
    try:
        resp = requests.get(HIBP_BREACHES_URL, headers=_HEADERS, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException:
        return []


def enrich_breaches_from_catalog(
    breaches: list[dict],
    catalog: dict[str, dict],
) -> list[dict]:
    """Merge breach data with local catalog entries (adds data_classes, pwn_count, etc.)."""
    enriched = []
    for b in breaches:
        name_key = b["name"].lower()
        entry = catalog.get(name_key)
        if entry:
            b = {
                **b,
                "domain": entry.get("domain") or b.get("domain", ""),
                "breach_date": entry.get("breach_date") or b.get("breach_date", ""),
                "pwn_count": entry.get("pwn_count") or b.get("pwn_count", 0),
                "data_classes": entry.get("data_classes") or b.get("data_classes", []),
                "is_sensitive": entry.get("is_sensitive", b.get("is_sensitive", False)),
                "is_verified": entry.get("is_verified", False),
            }
        enriched.append(b)
    return enriched


# ── HIBP domain endpoint (paid) ───────────────────────────────────────────────


def check_domain_breaches(domain: str, api_key: str) -> dict[str, Any]:
    """Call HIBP domain endpoint — requires paid plan."""
    if not api_key:
        return {
            "domain": domain,
            "accounts": [],
            "total": 0,
            "status": "unknown",
            "error": "HIBP API key not configured",
        }
    headers = {**_HEADERS, "hibp-api-key": api_key}
    try:
        resp = requests.get(
            HIBP_DOMAIN_URL.format(domain=domain), headers=headers, timeout=_TIMEOUT
        )
        if resp.status_code == 404:
            return {
                "domain": domain,
                "accounts": [],
                "total": 0,
                "status": "OK",
                "error": None,
            }
        if resp.status_code in (401, 403):
            return {
                "domain": domain,
                "accounts": [],
                "total": 0,
                "status": "unknown",
                "error": "Domain search requires a paid HIBP API key",
            }
        resp.raise_for_status()
        data = resp.json()
        accounts = [{"email": k, "breaches": v} for k, v in data.items()]
        total = len(accounts)
        status = "CRITICAL" if total >= 3 else ("WARNING" if total > 0 else "OK")
        return {
            "domain": domain,
            "accounts": accounts,
            "total": total,
            "status": status,
            "error": None,
        }
    except requests.exceptions.RequestException as exc:
        return {
            "domain": domain,
            "accounts": [],
            "total": 0,
            "status": "unknown",
            "error": str(exc),
        }
