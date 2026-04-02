"""
Module B2 — Secrets Detection
Scans files in a directory for leaked API keys, tokens, passwords, and private keys
using regex patterns. No external dependencies beyond the standard library.
"""

import os
import re
from typing import Any

# ---------------------------------------------------------------------------
# Secret patterns: (name, compiled regex)
# ---------------------------------------------------------------------------
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("AWS Access Key",        re.compile(r"AKIA[0-9A-Z]{16}")),
    ("AWS Secret Key",        re.compile(r"(?i)aws.{0,20}secret.{0,20}['\"][0-9a-zA-Z/+]{40}['\"]")),
    ("Generic API Key",       re.compile(r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]?[0-9a-zA-Z\-_]{20,}['\"]?")),
    ("Generic Secret",        re.compile(r"(?i)(secret[_-]?key|secret)\s*[=:]\s*['\"]?[0-9a-zA-Z\-_]{16,}['\"]?")),
    ("Generic Password",      re.compile(r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"][^'\"]{6,}['\"]")),
    ("Private Key Header",    re.compile(r"-----BEGIN (RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    ("Bearer Token",          re.compile(r"(?i)bearer\s+[0-9a-zA-Z\-_\.]{20,}")),
    ("GitHub Token",          re.compile(r"ghp_[0-9a-zA-Z]{36}")),
    ("Stripe Key",            re.compile(r"sk_(live|test)_[0-9a-zA-Z]{24,}")),
    ("Slack Token",           re.compile(r"xox[baprs]-[0-9a-zA-Z\-]{10,}")),
    ("Database URL",          re.compile(r"(?i)(postgres|mysql|mongodb|redis)://[^:]+:[^@]+@[^\s'\"]+")),
    ("JWT Token",             re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}")),
    ("Google API Key",        re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
    ("Sendgrid Key",          re.compile(r"SG\.[0-9A-Za-z\-_]{22}\.[0-9A-Za-z\-_]{43}")),
]

# Directories to skip entirely
SKIP_DIRS: set[str] = {
    ".venv", "venv", "env", ".env",
    "node_modules", ".git", "__pycache__",
    ".pytest_cache", "dist", "build",
}

# File extensions to scan (text-based only)
SCAN_EXTENSIONS: set[str] = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".env", ".cfg", ".ini",
    ".yml", ".yaml", ".json", ".toml", ".sh", ".bat", ".tf",
    ".conf", ".config", ".properties", ".xml", ".html",
}

MAX_FILE_SIZE_BYTES = 1_000_000  # Skip files > 1 MB


def _should_scan(path: str) -> bool:
    """Return True if the file should be scanned."""
    if os.path.getsize(path) > MAX_FILE_SIZE_BYTES:
        return False
    _, ext = os.path.splitext(path)
    # Always scan files with no extension that look like dotfiles (.env, .envrc)
    basename = os.path.basename(path)
    if basename.startswith(".") and not ext:
        return True
    return ext.lower() in SCAN_EXTENSIONS


def _scan_file(filepath: str) -> list[dict[str, Any]]:
    """Scan a single file for secret patterns. Returns list of findings."""
    findings: list[dict[str, Any]] = []
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                for pattern_name, regex in SECRET_PATTERNS:
                    match = regex.search(line)
                    if match:
                        # Redact the actual secret — show only first 6 chars + ***
                        raw = match.group(0)
                        preview = raw[:6] + "***" if len(raw) > 6 else "***"
                        findings.append({
                            "file": filepath,
                            "line": lineno,
                            "pattern": pattern_name,
                            "preview": preview,
                        })
                        break  # one finding per line max
    except (OSError, PermissionError):
        pass
    return findings


def check_secrets(scan_path: str) -> dict[str, Any]:
    """
    Recursively scan a directory (or single file) for leaked secrets.

    Args:
        scan_path: Absolute or relative path to a file or directory.

    Returns:
        A dict with keys:
            findings        — list of finding dicts
            total_files     — number of files scanned
            total_findings  — number of secrets detected
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message or None
    """
    result: dict[str, Any] = {
        "findings": [],
        "total_files": 0,
        "total_findings": 0,
        "status": "OK",
        "error": None,
    }

    if not os.path.exists(scan_path):
        result["error"] = f"Path not found: {scan_path}"
        result["status"] = "CRITICAL"
        return result

    all_findings: list[dict[str, Any]] = []
    files_scanned = 0

    if os.path.isfile(scan_path):
        if _should_scan(scan_path):
            all_findings.extend(_scan_file(scan_path))
            files_scanned = 1
    else:
        for dirpath, dirnames, filenames in os.walk(scan_path):
            # Prune skipped directories in-place so os.walk doesn't recurse into them
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if _should_scan(filepath):
                    all_findings.extend(_scan_file(filepath))
                    files_scanned += 1

    result["findings"] = all_findings
    result["total_files"] = files_scanned
    result["total_findings"] = len(all_findings)

    if len(all_findings) >= 3:
        result["status"] = "CRITICAL"
    elif all_findings:
        result["status"] = "WARNING"
    else:
        result["status"] = "OK"

    return result
