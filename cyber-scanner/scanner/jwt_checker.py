"""
Module H5 — JWT Security Checker (Tier 4)
Detects JWT tokens in HTTP responses (headers, cookies, body) and
checks for known misconfigurations: alg:none, weak secrets, missing exp.
No API key required.
"""

import base64
import hashlib
import hmac
import json
import re
import time
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8

# Common weak secrets used in dev/demo environments
WEAK_SECRETS = [
    "secret", "password", "changeme", "test", "1234", "admin",
    "jwt_secret", "mysecret", "supersecret", "your-256-bit-secret",
    "your-secret-key", "default", "key", "abcdef", "123456", "qwerty",
]

JWT_PATTERN = re.compile(
    r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*"
)


def _fetch_response(url: str) -> dict[str, Any] | None:
    """Fetch URL and return {headers, cookies, body} or None."""
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,  # nosec B501 nosemgrep: python.requests.security.verify-disabled
            allow_redirects=True,
        )
        return {
            "headers": dict(resp.headers),
            "cookies": {k: v for k, v in resp.cookies.items()},
            "body":    resp.text[:20_000],
            "status_code": resp.status_code,
        }
    except requests.exceptions.RequestException:
        return None


def _extract_jwts(response: dict[str, Any]) -> list[str]:
    """Extract JWT tokens from headers, cookies, and body."""
    tokens: list[str] = []

    # Headers (Authorization: Bearer <token>)
    for header_val in response["headers"].values():
        found = JWT_PATTERN.findall(str(header_val))
        tokens.extend(found)

    # Cookies
    for cookie_val in response["cookies"].values():
        found = JWT_PATTERN.findall(str(cookie_val))
        tokens.extend(found)

    # Body (JSON responses, JS variables)
    found = JWT_PATTERN.findall(response["body"])
    tokens.extend(found)

    return list(set(tokens))


def _decode_jwt_payload(token: str) -> dict[str, Any] | None:
    """Base64url-decode the JWT payload. Returns dict or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        payload_b64 = parts[1]
        # Pad to multiple of 4
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        return json.loads(payload_bytes)
    except Exception:
        return None


def _decode_jwt_header(token: str) -> dict[str, Any] | None:
    """Base64url-decode the JWT header. Returns dict or None."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64 = parts[0]
        padding = 4 - len(header_b64) % 4
        if padding != 4:
            header_b64 += "=" * padding
        header_bytes = base64.urlsafe_b64decode(header_b64)
        return json.loads(header_bytes)
    except Exception:
        return None


def _check_alg_none(header: dict[str, Any]) -> bool:
    """Return True if algorithm is 'none' (critical vulnerability)."""
    return str(header.get("alg", "")).lower() == "none"


def _check_exp(payload: dict[str, Any]) -> bool:
    """Return True if token has no expiration claim."""
    return "exp" not in payload


def _check_weak_secret(token: str) -> str | None:
    """
    Try to brute-force the HMAC secret against a list of weak secrets.
    Returns the secret if found, else None.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    signing_input = f"{parts[0]}.{parts[1]}".encode()
    sig_b64 = parts[2]
    padding = 4 - len(sig_b64) % 4
    if padding != 4:
        sig_b64 += "=" * padding
    try:
        expected_sig = base64.urlsafe_b64decode(sig_b64)
    except Exception:
        return None

    for secret in WEAK_SECRETS:
        computed = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if hmac.compare_digest(computed, expected_sig):
            return secret
    return None


def _analyse_token(token: str) -> dict[str, Any]:
    """Full analysis of a single JWT token."""
    header  = _decode_jwt_header(token)
    payload = _decode_jwt_payload(token)

    issues: list[str] = []
    alg_none    = False
    no_exp      = False
    weak_secret = None

    if header:
        alg_none = _check_alg_none(header)
        if alg_none:
            issues.append("alg:none — signature bypassed")

    if payload:
        no_exp = _check_exp(payload)
        if no_exp:
            issues.append("No expiration (exp claim missing)")

    # Only brute-force HMAC-based algorithms
    if header and str(header.get("alg", "")).upper().startswith("HS"):
        weak_secret = _check_weak_secret(token)
        if weak_secret:
            issues.append(f"Weak secret detected: '{weak_secret}'")

    severity = "OK"
    if alg_none or weak_secret:
        severity = "CRITICAL"
    elif no_exp:
        severity = "WARNING"

    return {
        "token":       token[:60] + "…",
        "header":      header,
        "payload":     payload,
        "alg_none":    alg_none,
        "no_exp":      no_exp,
        "weak_secret": weak_secret,
        "issues":      issues,
        "severity":    severity,
    }


def check_jwt(url: str) -> dict[str, Any]:
    """
    Detect and analyse JWT tokens exposed by the target URL.

    Args:
        url: Full URL to probe (e.g. "https://example.com")

    Returns:
        A dict with keys:
            tokens_found    — number of JWT tokens detected
            analyses        — list of per-token analysis results
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "tokens_found": 0,
        "analyses":     [],
        "status":       "OK",
        "error":        None,
    }

    response = _fetch_response(url)
    if not response:
        result["error"]  = "Failed to fetch target URL"
        result["status"] = "CRITICAL"
        return result

    tokens = _extract_jwts(response)
    result["tokens_found"] = len(tokens)

    if not tokens:
        return result

    analyses = [_analyse_token(t) for t in tokens]
    result["analyses"] = analyses

    severities = [a["severity"] for a in analyses]
    if "CRITICAL" in severities:
        result["status"] = "CRITICAL"
    elif "WARNING" in severities:
        result["status"] = "WARNING"

    return result
