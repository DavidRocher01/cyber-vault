"""Dark web surveillance — HaveIBeenPwned email breach checker."""
from __future__ import annotations

from typing import Any

import requests

HIBP_EMAIL_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
HIBP_DOMAIN_URL = "https://haveibeenpwned.com/api/v3/breacheddomain/{domain}"
_HEADERS = {"User-Agent": "CyberScan/2.0"}
_TIMEOUT = 10


def check_email_breaches(email: str, api_key: str) -> dict[str, Any]:
    """Call HIBP and return normalised breach data for an email address."""
    if not api_key:
        return {"email": email, "breaches": [], "total": 0, "status": "unknown",
                "error": "HIBP API key not configured"}
    headers = {**_HEADERS, "hibp-api-key": api_key}
    try:
        resp = requests.get(
            HIBP_EMAIL_URL.format(email=email),
            headers=headers,
            timeout=_TIMEOUT,
            params={"truncateResponse": "false"},
        )
        if resp.status_code == 404:
            return {"email": email, "breaches": [], "total": 0, "status": "OK", "error": None}
        if resp.status_code == 401:
            return {"email": email, "breaches": [], "total": 0, "status": "unknown",
                    "error": "Invalid API key"}
        if resp.status_code == 429:
            return {"email": email, "breaches": [], "total": 0, "status": "unknown",
                    "error": "Rate limited — retry later"}
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
        return {"email": email, "breaches": breaches, "total": total, "status": status, "error": None}
    except requests.exceptions.RequestException as exc:
        return {"email": email, "breaches": [], "total": 0, "status": "unknown", "error": str(exc)}


def check_domain_breaches(domain: str, api_key: str) -> dict[str, Any]:
    """Call HIBP domain endpoint (requires paid plan)."""
    if not api_key:
        return {"domain": domain, "accounts": [], "total": 0, "status": "unknown",
                "error": "HIBP API key not configured"}
    headers = {**_HEADERS, "hibp-api-key": api_key}
    try:
        resp = requests.get(HIBP_DOMAIN_URL.format(domain=domain), headers=headers, timeout=_TIMEOUT)
        if resp.status_code == 404:
            return {"domain": domain, "accounts": [], "total": 0, "status": "OK", "error": None}
        if resp.status_code in (401, 403):
            return {"domain": domain, "accounts": [], "total": 0, "status": "unknown",
                    "error": "Domain search requires a paid HIBP API key"}
        resp.raise_for_status()
        data = resp.json()
        accounts = [{"email": k, "breaches": v} for k, v in data.items()]
        total = len(accounts)
        status = "CRITICAL" if total >= 3 else ("WARNING" if total > 0 else "OK")
        return {"domain": domain, "accounts": accounts, "total": total, "status": status, "error": None}
    except requests.exceptions.RequestException as exc:
        return {"domain": domain, "accounts": [], "total": 0, "status": "unknown", "error": str(exc)}
