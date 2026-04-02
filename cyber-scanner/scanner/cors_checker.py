"""
Module E3 — CORS Audit
Detects dangerous CORS misconfigurations by sending crafted Origin headers
and analysing Access-Control-Allow-Origin / Access-Control-Allow-Credentials.
"""

import requests
import urllib3
from typing import Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

EVIL_ORIGIN = "https://evil-attacker.com"
NULL_ORIGIN = "null"


def _probe(url: str, origin: str, timeout: int = 10) -> dict[str, str]:
    """Send a GET request with a crafted Origin and return relevant response headers."""
    try:
        response = requests.get(
            url,
            headers={"Origin": origin},
            timeout=timeout,
            verify=False,
            allow_redirects=True,
        )
        acao = response.headers.get("Access-Control-Allow-Origin", "")
        acac = response.headers.get("Access-Control-Allow-Credentials", "").lower()
        acam = response.headers.get("Access-Control-Allow-Methods", "")
        return {"acao": acao, "acac": acac, "acam": acam, "status_code": str(response.status_code)}
    except requests.exceptions.RequestException:
        return {"acao": "", "acac": "", "acam": "", "status_code": "error"}


def check_cors(url: str) -> dict[str, Any]:
    """
    Audit CORS configuration by probing with crafted Origin headers.

    Detects:
    - Wildcard (*) with credentials → critical
    - Reflected origin with credentials → critical
    - Wildcard without credentials → warning
    - Null origin accepted → warning

    Args:
        url: Full URL to probe (e.g. "https://example.com")

    Returns:
        A dict with keys:
            allow_origin        — value of Access-Control-Allow-Origin
            allow_credentials   — value of Access-Control-Allow-Credentials
            allow_methods       — value of Access-Control-Allow-Methods
            issues              — list of vulnerability strings
            vulnerable          — True if at least one critical issue found
            status              — "OK" | "WARNING" | "CRITICAL"
            error               — error message or None
    """
    result: dict[str, Any] = {
        "allow_origin": "",
        "allow_credentials": "",
        "allow_methods": "",
        "issues": [],
        "vulnerable": False,
        "status": "OK",
        "error": None,
    }

    try:
        # Probe 1: arbitrary evil origin
        evil_probe = _probe(url, EVIL_ORIGIN)
        if evil_probe["status_code"] == "error":
            result["error"] = "Failed to connect to target"
            result["status"] = "CRITICAL"
            return result

        acao = evil_probe["acao"]
        acac = evil_probe["acac"]

        result["allow_origin"] = acao
        result["allow_credentials"] = acac
        result["allow_methods"] = evil_probe["acam"]

        issues: list[str] = []

        # Critical: wildcard + credentials
        if acao == "*" and acac == "true":
            issues.append(
                "CRITIQUE : Access-Control-Allow-Origin: * combiné avec "
                "Access-Control-Allow-Credentials: true — vol de session possible"
            )
            result["vulnerable"] = True

        # Critical: origin reflected back + credentials
        elif acao == EVIL_ORIGIN and acac == "true":
            issues.append(
                "CRITIQUE : Origin arbitraire reflété avec credentials=true — "
                "CORS bypass complet, vol de données authentifiées possible"
            )
            result["vulnerable"] = True

        # Warning: wildcard without credentials (API data exposed)
        elif acao == "*":
            issues.append(
                "AVERTISSEMENT : Access-Control-Allow-Origin: * — "
                "toutes les origines peuvent lire les réponses de l'API"
            )

        # Warning: origin reflected without credentials
        elif acao == EVIL_ORIGIN:
            issues.append(
                "AVERTISSEMENT : Origin arbitraire reflété sans vérification — "
                "considérer une liste blanche d'origines autorisées"
            )

        # Probe 2: null origin
        null_probe = _probe(url, NULL_ORIGIN)
        if null_probe["acao"] == "null":
            issues.append(
                "AVERTISSEMENT : Origin: null accepté — "
                "exploitable depuis des iframes sandboxées ou des fichiers locaux"
            )

        result["issues"] = issues

        if result["vulnerable"]:
            result["status"] = "CRITICAL"
        elif issues:
            result["status"] = "WARNING"
        else:
            result["status"] = "OK"

    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"
        result["status"] = "CRITICAL"

    return result
