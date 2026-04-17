import requests
import urllib3
from typing import Any

from scanner.constants import SECURITY_HEADERS

# Suppress InsecureRequestWarning when verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def check_headers(url: str) -> dict[str, Any]:
    """
    Check security headers for a given URL.

    Args:
        url: The full URL to check (e.g. "https://example.com")

    Returns:
        A dict with keys: status_code, headers_found, headers_missing, score, status
    """
    result: dict[str, Any] = {
        "status_code": None,
        "headers_found": [],
        "headers_missing": [],
        "score": 0,
        "status": "CRITICAL",
        "error": None,
    }

    try:
        response = requests.get(url, timeout=10, verify=False)  # nosec B501 nosemgrep: python.requests.security.verify-disabled
        result["status_code"] = response.status_code

        headers_found: list[str] = []
        headers_missing: list[str] = []

        # Build the lowercased set once for O(1) lookups instead of rebuilding per header
        response_headers_lower = {h.lower() for h in response.headers}

        for header in SECURITY_HEADERS:
            if header.lower() in response_headers_lower:
                headers_found.append(header)
            else:
                headers_missing.append(header)

        score: int = len(headers_found)
        result["headers_found"] = headers_found
        result["headers_missing"] = headers_missing
        result["score"] = score

        if score == 6:
            result["status"] = "OK"
        elif score >= 4:
            result["status"] = "WARNING"
        else:
            result["status"] = "CRITICAL"

    except requests.exceptions.ConnectionError as e:
        result["error"] = f"Connection error: {e}"
        result["status"] = "CRITICAL"
    except requests.exceptions.Timeout:
        result["error"] = "Request timed out after 10 seconds"
        result["status"] = "CRITICAL"
    except requests.exceptions.TooManyRedirects:
        result["error"] = "Too many redirects"
        result["status"] = "CRITICAL"
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request failed: {e}"
        result["status"] = "CRITICAL"
    except Exception as e:
        result["error"] = f"Unexpected error: {e}"
        result["status"] = "CRITICAL"

    return result
