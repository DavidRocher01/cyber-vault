"""
Module B — Software Composition Analysis (SCA)
Queries the OSV.dev API to find known CVEs in project dependencies.
Supports requirements.txt (PyPI) and package.json (npm).
"""

import json
import os
from typing import Any

import requests

OSV_API_URL = "https://api.osv.dev/v1/query"
REQUEST_TIMEOUT = 10


def _parse_requirements_txt(path: str) -> list[dict[str, str | None]]:
    """Parse a requirements.txt and return [{name, version}, ...]."""
    packages: list[dict[str, str | None]] = []
    with open(path, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith(("#", "-")):
                continue
            # Drop inline comments and extras like package[security]>=1.0
            line = line.split("#")[0].strip()
            name_part = line.split("[")[0]
            version: str | None = None
            for sep in ("==", ">=", "<=", "~=", "!=", ">", "<"):
                if sep in name_part or sep in line:
                    # Split on first version specifier found
                    idx = line.index(sep)
                    name_part = line[:idx].split("[")[0].strip()
                    version = line[idx + len(sep):].split(",")[0].strip()
                    break
            packages.append({"name": name_part.strip(), "version": version})
    return packages


def _parse_package_json(path: str) -> list[dict[str, str | None]]:
    """Parse a package.json and return [{name, version}, ...] for all dependencies."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    packages: list[dict[str, str | None]] = []
    for section in ("dependencies", "devDependencies"):
        for name, raw_version in data.get(section, {}).items():
            # Strip range prefixes: ^1.2.3 → 1.2.3
            clean = raw_version.lstrip("^~>=< ").split(" ")[0].strip()
            packages.append({"name": name, "version": clean or None})
    return packages


def _query_osv(name: str, version: str | None, ecosystem: str) -> list[dict[str, Any]]:
    """
    Call the OSV.dev batch query endpoint for one package.
    Returns the list of vulnerability objects (may be empty).
    """
    payload: dict[str, Any] = {"package": {"name": name, "ecosystem": ecosystem}}
    if version:
        payload["version"] = version

    try:
        response = requests.post(OSV_API_URL, json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json().get("vulns", [])
    except requests.exceptions.RequestException:
        return []


def _extract_severity(vuln: dict[str, Any]) -> str:
    """
    Extract a human-readable severity from an OSV vulnerability object.
    Prefers database_specific.severity, falls back to UNKNOWN.
    """
    db_specific = vuln.get("database_specific") or {}
    if isinstance(db_specific, dict):
        sev = str(db_specific.get("severity", "")).upper()
        if sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            return sev

    # Some ecosystems store severity in ecosystem_specific
    eco_specific = vuln.get("ecosystem_specific") or {}
    if isinstance(eco_specific, dict):
        sev = str(eco_specific.get("severity", "")).upper()
        if sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
            return sev

    return "UNKNOWN"


def check_sca(
    requirements_path: str | None = None,
    package_json_path: str | None = None,
) -> dict[str, Any]:
    """
    Run SCA on requirements.txt and/or package.json via OSV.dev.

    Args:
        requirements_path: Absolute or relative path to requirements.txt (optional).
        package_json_path: Absolute or relative path to package.json (optional).

    Returns:
        A dict with keys:
            vulns           — list of vulnerability dicts
            total_packages  — number of packages scanned
            total_vulns     — number of vulnerabilities found
            status          — "OK" | "WARNING" | "CRITICAL"
            error           — error message string or None
    """
    result: dict[str, Any] = {
        "vulns": [],
        "total_packages": 0,
        "total_vulns": 0,
        "status": "OK",
        "error": None,
    }

    if not requirements_path and not package_json_path:
        result["error"] = "No dependency file provided. Pass --requirements and/or --package-json."
        result["status"] = "CRITICAL"
        return result

    # (name, version | None, ecosystem)
    all_packages: list[tuple[str, str | None, str]] = []

    if requirements_path:
        if not os.path.exists(requirements_path):
            result["error"] = f"File not found: {requirements_path}"
            result["status"] = "CRITICAL"
            return result
        try:
            for pkg in _parse_requirements_txt(requirements_path):
                all_packages.append((pkg["name"], pkg["version"], "PyPI"))
        except Exception as exc:
            result["error"] = f"Failed to parse {requirements_path}: {exc}"
            result["status"] = "CRITICAL"
            return result

    if package_json_path:
        if not os.path.exists(package_json_path):
            result["error"] = f"File not found: {package_json_path}"
            result["status"] = "CRITICAL"
            return result
        try:
            for pkg in _parse_package_json(package_json_path):
                all_packages.append((pkg["name"], pkg["version"], "npm"))
        except Exception as exc:
            result["error"] = f"Failed to parse {package_json_path}: {exc}"
            result["status"] = "CRITICAL"
            return result

    result["total_packages"] = len(all_packages)
    vulns_found: list[dict[str, Any]] = []

    for name, version, ecosystem in all_packages:
        for vuln in _query_osv(name, version, ecosystem):
            # Prefer CVE aliases, fall back to OSV ID
            cve_ids = [a for a in vuln.get("aliases", []) if a.startswith("CVE-")]
            if not cve_ids:
                cve_ids = [vuln.get("id", "N/A")]

            vulns_found.append({
                "package": name,
                "version": version or "unspecified",
                "ecosystem": ecosystem,
                "cve_ids": cve_ids,
                "severity": _extract_severity(vuln),
                "summary": (vuln.get("summary") or "No description available.")[:200],
            })

    result["vulns"] = vulns_found
    result["total_vulns"] = len(vulns_found)

    if any(v["severity"] in ("CRITICAL", "HIGH") for v in vulns_found):
        result["status"] = "CRITICAL"
    elif vulns_found:
        result["status"] = "WARNING"
    else:
        result["status"] = "OK"

    return result
