"""
Module F3 — Data Breach Checker
Checks if an email address or domain appears in known data breaches
using the HaveIBeenPwned (HIBP) API v3.

API key required for domain search (paid).
Email breach check uses the free HIBP API (rate-limited to 1 req/1.5s).
"""

import time
from typing import Any

import requests

HIBP_EMAIL_URL = "https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
HIBP_DOMAIN_URL = "https://haveibeenpwned.com/api/v3/breacheddomain/{domain}"
HIBP_HEADERS_BASE = {
    "User-Agent": "Cyber-Scanner/1.0",
}
REQUEST_TIMEOUT = 10


def _check_email(email: str, api_key: str) -> dict[str, Any]:
    """Query HIBP for breaches containing the given email."""
    url = HIBP_EMAIL_URL.format(email=email)
    headers = {**HIBP_HEADERS_BASE, "hibp-api-key": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, params={"truncateResponse": "false"})
        if resp.status_code == 404:
            return {"breaches": [], "total": 0}
        if resp.status_code == 401:
            return {"error": "Invalid API key"}
        if resp.status_code == 429:
            return {"error": "Rate limited — retry after 1.5 seconds"}
        resp.raise_for_status()
        breaches = resp.json()
        return {
            "breaches": [
                {
                    "name": b["Name"],
                    "domain": b.get("Domain", ""),
                    "breach_date": b.get("BreachDate", ""),
                    "pwn_count": b.get("PwnCount", 0),
                    "data_classes": b.get("DataClasses", []),
                }
                for b in breaches
            ],
            "total": len(breaches),
        }
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def _check_domain(domain: str, api_key: str) -> dict[str, Any]:
    """Query HIBP for all email accounts in a domain that have been breached."""
    url = HIBP_DOMAIN_URL.format(domain=domain)
    headers = {**HIBP_HEADERS_BASE, "hibp-api-key": api_key}
    try:
        resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 404:
            return {"accounts": [], "total": 0}
        if resp.status_code == 401:
            return {"error": "Invalid API key"}
        if resp.status_code == 403:
            return {"error": "Domain search requires a paid HIBP API key"}
        resp.raise_for_status()
        data = resp.json()
        # Response is a dict of {email: [breach_names]}
        accounts = [{"email": k, "breaches": v} for k, v in data.items()]
        return {"accounts": accounts, "total": len(accounts)}
    except requests.exceptions.RequestException as exc:
        return {"error": str(exc)}


def check_breach(
    target: str,
    api_key: str | None = None,
    mode: str = "email",
) -> dict[str, Any]:
    """
    Check if an email or domain appears in HaveIBeenPwned breaches.

    Args:
        target:  Email address or domain name to check.
        api_key: HIBP API key. Required for domain mode, optional for email.
        mode:    "email" | "domain"

    Returns:
        A dict with keys:
            target          — the checked email or domain
            mode            — "email" | "domain"
            breaches        — list of breach dicts (email mode)
            accounts        — list of {email, breaches} dicts (domain mode)
            total           — number of breaches / accounts found
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "target": target,
        "mode": mode,
        "breaches": [],
        "accounts": [],
        "total": 0,
        "status": "OK",
        "error": None,
    }

    if not api_key:
        result["error"] = (
            "HIBP API key required. Get one at https://haveibeenpwned.com/API/Key. "
            "Pass it via --hibp-key."
        )
        result["status"] = "WARNING"
        return result

    if mode == "email":
        data = _check_email(target, api_key)
        if "error" in data:
            result["error"] = data["error"]
            result["status"] = "CRITICAL"
            return result
        result["breaches"] = data["breaches"]
        result["total"] = data["total"]
    else:
        data = _check_domain(target, api_key)
        if "error" in data:
            result["error"] = data["error"]
            result["status"] = "CRITICAL"
            return result
        result["accounts"] = data["accounts"]
        result["total"] = data["total"]

    if result["total"] >= 3:
        result["status"] = "CRITICAL"
    elif result["total"] > 0:
        result["status"] = "WARNING"
    else:
        result["status"] = "OK"

    return result
