"""
Module E2 — Cookie Security
Checks Set-Cookie headers for missing security flags:
HttpOnly, Secure, SameSite.
"""

import requests
import urllib3
from typing import Any

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cookies that should always have the Secure flag
SENSITIVE_COOKIE_PATTERNS: list[str] = [
    "session", "sess", "auth", "token", "jwt",
    "access", "refresh", "csrf", "xsrf", "sid",
]


def _parse_set_cookie(header_value: str) -> dict[str, Any]:
    """
    Parse a single Set-Cookie header value into a structured dict.
    Returns: {name, http_only, secure, same_site, value_preview}
    """
    parts = [p.strip() for p in header_value.split(";")]
    name = parts[0].split("=")[0].strip() if parts else "unknown"
    value_preview = parts[0].split("=", 1)[1][:6] + "***" if "=" in parts[0] else "***"

    flags = {p.lower() for p in parts[1:]}
    flags_str = " ".join(flags)

    http_only = "httponly" in flags_str
    secure = "secure" in flags_str

    same_site = "none"
    for part in parts[1:]:
        if part.strip().lower().startswith("samesite="):
            same_site = part.strip().split("=", 1)[1].strip().lower()
            break

    return {
        "name": name,
        "value_preview": value_preview,
        "http_only": http_only,
        "secure": secure,
        "same_site": same_site,
    }


def _is_sensitive(cookie_name: str) -> bool:
    """Return True if the cookie name suggests it holds sensitive data."""
    lower = cookie_name.lower()
    return any(pattern in lower for pattern in SENSITIVE_COOKIE_PATTERNS)


def check_cookies(url: str) -> dict[str, Any]:
    """
    Analyse cookies returned by the server for security flag issues.

    Args:
        url: Full URL to request (e.g. "https://example.com")

    Returns:
        A dict with keys:
            cookies         — list of parsed cookie dicts
            issues          — list of {cookie, issue} dicts
            total_cookies   — number of cookies found
            total_issues    — number of flag violations
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "cookies": [],
        "issues": [],
        "total_cookies": 0,
        "total_issues": 0,
        "status": "OK",
        "error": None,
    }

    try:
        response = requests.get(url, timeout=10, verify=False, allow_redirects=True)

        raw_cookies = response.headers.getlist("Set-Cookie") if hasattr(response.headers, "getlist") \
            else [v for k, v in response.headers.items() if k.lower() == "set-cookie"]

        # requests merges duplicate headers — use raw response headers
        raw_cookies = []
        for k, v in response.raw.headers.items():
            if k.lower() == "set-cookie":
                raw_cookies.append(v)

        if not raw_cookies:
            # Fallback: use the parsed cookies from requests
            for cookie in response.cookies:
                raw_cookies.append(
                    f"{cookie.name}={cookie.value}; "
                    f"{'HttpOnly; ' if cookie.has_nonstandard_attr('HttpOnly') else ''}"
                    f"{'Secure; ' if cookie.secure else ''}"
                    f"SameSite={cookie.get_nonstandard_attr('SameSite', 'None')}"
                )

        parsed: list[dict[str, Any]] = [_parse_set_cookie(c) for c in raw_cookies]
        issues: list[dict[str, str]] = []

        for cookie in parsed:
            name = cookie["name"]
            if not cookie["http_only"]:
                issues.append({"cookie": name, "issue": "HttpOnly manquant — accessible via JavaScript"})
            if not cookie["secure"]:
                issues.append({"cookie": name, "issue": "Secure manquant — transmis en clair sur HTTP"})
            if cookie["same_site"] in ("none", ""):
                issues.append({"cookie": name, "issue": "SameSite non défini — risque CSRF"})
            elif cookie["same_site"] == "none" and not cookie["secure"]:
                issues.append({"cookie": name, "issue": "SameSite=None sans Secure — invalide"})

        result["cookies"] = parsed
        result["issues"] = issues
        result["total_cookies"] = len(parsed)
        result["total_issues"] = len(issues)

        if len(issues) >= 3:
            result["status"] = "CRITICAL"
        elif issues:
            result["status"] = "WARNING"
        else:
            result["status"] = "OK"

    except requests.exceptions.ConnectionError as exc:
        result["error"] = f"Connection error: {exc}"
        result["status"] = "CRITICAL"
    except requests.exceptions.Timeout:
        result["error"] = "Request timed out after 10 seconds"
        result["status"] = "CRITICAL"
    except requests.exceptions.RequestException as exc:
        result["error"] = f"Request failed: {exc}"
        result["status"] = "CRITICAL"
    except Exception as exc:
        result["error"] = f"Unexpected error: {exc}"
        result["status"] = "CRITICAL"

    return result
