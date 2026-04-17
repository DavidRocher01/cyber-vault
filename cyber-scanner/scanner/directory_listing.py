"""
Module H3 — Directory Listing & Sensitive Path Detection (Tier 4)
Probes common sensitive paths for directory listings, exposed files,
and admin interfaces. No API key required.
"""

import re
from typing import Any

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8

# Paths to probe and their risk level
SENSITIVE_PATHS: list[dict[str, Any]] = [
    # --- Directory listing indicators ---
    {"path": "/.git/",              "category": "source_code",  "severity": "CRITICAL", "pattern": r"Index of|\.git"},
    {"path": "/.git/config",        "category": "source_code",  "severity": "CRITICAL", "pattern": r"\[core\]"},
    {"path": "/.env",               "category": "secrets",      "severity": "CRITICAL", "pattern": r"(?i)(DB_|APP_|SECRET|API_KEY|PASSWORD)"},
    {"path": "/.env.backup",        "category": "secrets",      "severity": "CRITICAL", "pattern": r"(?i)(DB_|APP_|SECRET)"},
    {"path": "/backup/",            "category": "backup",       "severity": "CRITICAL", "pattern": r"Index of|backup"},
    {"path": "/backup.zip",         "category": "backup",       "severity": "CRITICAL", "pattern": None},
    {"path": "/backup.tar.gz",      "category": "backup",       "severity": "CRITICAL", "pattern": None},
    {"path": "/db.sql",             "category": "database",     "severity": "CRITICAL", "pattern": r"(?i)(CREATE TABLE|INSERT INTO)"},
    {"path": "/database.sql",       "category": "database",     "severity": "CRITICAL", "pattern": r"(?i)(CREATE TABLE|INSERT INTO)"},
    {"path": "/wp-config.php.bak",  "category": "secrets",      "severity": "CRITICAL", "pattern": None},
    {"path": "/config.php.bak",     "category": "secrets",      "severity": "CRITICAL", "pattern": None},
    # --- Admin interfaces ---
    {"path": "/admin/",             "category": "admin",        "severity": "WARNING",  "pattern": None},
    {"path": "/administrator/",     "category": "admin",        "severity": "WARNING",  "pattern": None},
    {"path": "/phpmyadmin/",        "category": "admin",        "severity": "CRITICAL", "pattern": r"(?i)phpmyadmin"},
    {"path": "/adminer.php",        "category": "admin",        "severity": "CRITICAL", "pattern": r"(?i)adminer"},
    {"path": "/_cpanel/",           "category": "admin",        "severity": "WARNING",  "pattern": None},
    # --- Exposed config / info ---
    {"path": "/server-status",      "category": "info",         "severity": "WARNING",  "pattern": r"Apache Server Status"},
    {"path": "/server-info",        "category": "info",         "severity": "WARNING",  "pattern": r"Apache Server Information"},
    {"path": "/.htaccess",          "category": "config",       "severity": "WARNING",  "pattern": r"(?i)(RewriteRule|Options|Deny|Allow)"},
    {"path": "/web.config",         "category": "config",       "severity": "WARNING",  "pattern": r"(?i)(configuration|connectionStrings)"},
    {"path": "/phpinfo.php",        "category": "info",         "severity": "CRITICAL", "pattern": r"phpinfo\(\)"},
    {"path": "/info.php",           "category": "info",         "severity": "CRITICAL", "pattern": r"phpinfo\(\)"},
    # --- Directory listing ---
    {"path": "/uploads/",           "category": "listing",      "severity": "WARNING",  "pattern": r"Index of"},
    {"path": "/files/",             "category": "listing",      "severity": "WARNING",  "pattern": r"Index of"},
    {"path": "/logs/",              "category": "listing",      "severity": "CRITICAL", "pattern": r"Index of"},
    {"path": "/tmp/",               "category": "listing",      "severity": "CRITICAL", "pattern": r"Index of"},  # nosec B108 — literal path tested on remote target, not local
]

DIRECTORY_LISTING_PATTERNS = [
    r"Index of /",
    r"Directory listing for",
    r"<title>Index of",
]


def _probe_path(base_url: str, path_def: dict[str, Any]) -> dict[str, Any] | None:
    """
    Probe a single path. Returns a finding dict if exposed, else None.
    """
    url = base_url.rstrip("/") + path_def["path"]
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,  # nosec B501 nosemgrep: python.requests.security.verify-disabled
            allow_redirects=False,
        )
        if resp.status_code not in (200, 403):
            return None

        body = resp.text[:10_000]
        pattern = path_def.get("pattern")

        # Check body pattern if defined
        if pattern:
            if not re.search(pattern, body, re.IGNORECASE):
                return None
        elif resp.status_code != 200:
            return None

        # Check for directory listing
        is_listing = any(
            re.search(p, body, re.IGNORECASE)
            for p in DIRECTORY_LISTING_PATTERNS
        )

        return {
            "path":     path_def["path"],
            "url":      url,
            "category": path_def["category"],
            "severity": path_def["severity"],
            "status_code": resp.status_code,
            "is_listing":  is_listing,
        }
    except requests.exceptions.RequestException:
        return None


def _severity_rank(severity: str) -> int:
    """Return sort rank for severity."""
    return {"CRITICAL": 0, "WARNING": 1}.get(severity, 2)


def check_directory_listing(url: str) -> dict[str, Any]:
    """
    Probe a URL for exposed directories and sensitive paths.

    Args:
        url: Base URL to probe (e.g. "https://example.com")

    Returns:
        A dict with keys:
            findings        — list of exposed path findings
            total_critical  — number of CRITICAL findings
            total_warning   — number of WARNING findings
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "findings":      [],
        "total_critical": 0,
        "total_warning":  0,
        "status":         "OK",
        "error":          None,
    }

    findings = []
    for path_def in SENSITIVE_PATHS:
        finding = _probe_path(url, path_def)
        if finding:
            findings.append(finding)

    findings.sort(key=lambda f: _severity_rank(f["severity"]))

    result["findings"]       = findings
    result["total_critical"] = sum(1 for f in findings if f["severity"] == "CRITICAL")
    result["total_warning"]  = sum(1 for f in findings if f["severity"] == "WARNING")

    if result["total_critical"] > 0:
        result["status"] = "CRITICAL"
    elif result["total_warning"] > 0:
        result["status"] = "WARNING"

    return result
