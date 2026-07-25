"""
deps.py — software-composition / dependency vulnerability runners.

CVE scanners over declared dependencies and lockfiles: pip-audit & safety
(Python), npm audit (Node), trivy / grype / osv-scanner (multi-ecosystem).
Each returns a list of normalised finding dicts.
"""

from __future__ import annotations

import json
import os

from loguru import logger

from . import base


def _run_npm_audit(repo_dir: str) -> list[dict]:
    """Run npm audit if package.json is present. Supports npm 7+ JSON v2 format."""
    if not os.path.isfile(os.path.join(repo_dir, "package.json")):
        logger.info("npm audit: no package.json found, skipping")
        return []

    if not os.path.isfile(os.path.join(repo_dir, "package-lock.json")):
        if os.path.isdir(os.path.join(repo_dir, "node_modules")):
            logger.info(
                "npm audit: node_modules present but no lock file, skipping to avoid slow install"
            )
            return []
        logger.info("npm audit: generating package-lock.json")
        rc, _, _ = base._run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit"],
            cwd=repo_dir,
            timeout=60,
        )
        if rc != 0:
            logger.warning("npm audit: failed to generate package-lock.json, skipping")
            return []

    _code, stdout, stderr = base._run(
        ["npm", "audit", "--json"],
        cwd=repo_dir,
        timeout=120,
    )
    if not stdout:
        logger.warning(f"npm audit produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"npm audit JSON parse error: {stdout[:200]}")
        return []

    severity_map = {
        "critical": "critical",
        "high": "high",
        "moderate": "medium",
        "low": "low",
        "info": "low",
    }

    findings = []
    for pkg_name, vuln in data.get("vulnerabilities", {}).items():
        via = vuln.get("via", [])
        advisories = [v for v in via if isinstance(v, dict)]
        if advisories:
            for adv in advisories:
                sev = severity_map.get(adv.get("severity", vuln.get("severity", "low")), "low")
                findings.append(
                    {
                        "tool": "npm-audit",
                        "severity": sev,
                        "rule": str(adv.get("source", "")),
                        "title": adv.get("title", f"Vulnérabilité dans {pkg_name}"),
                        "message": adv.get("url", adv.get("title", "")),
                        "file": "package.json",
                        "line": None,
                        "confidence": "high",
                        "fix_versions": [],
                    }
                )
        else:
            sev = severity_map.get(vuln.get("severity", "low"), "low")
            findings.append(
                {
                    "tool": "npm-audit",
                    "severity": sev,
                    "rule": "",
                    "title": f"Vulnérabilité dans {pkg_name}",
                    "message": f"Paquet affecté : {pkg_name} ({vuln.get('range', '')})",
                    "file": "package.json",
                    "line": None,
                    "confidence": "high",
                    "fix_versions": [],
                }
            )
    return findings


def _run_trivy(repo_dir: str) -> list[dict]:
    """Run trivy fs for multi-ecosystem CVE detection (pip, npm, go, cargo, …)."""
    data = base._run_json_tool(
        ["trivy", "fs", ".", "--format", "json", "--quiet", "--no-progress"],
        repo_dir,
        "trivy",
        timeout=180,
    )
    if data is None:
        return []

    severity_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
        "UNKNOWN": "low",
    }

    findings = []
    for result in data.get("Results", []):
        target = result.get("Target", "")
        for vuln in result.get("Vulnerabilities", []) or []:
            sev = severity_map.get(vuln.get("Severity", "UNKNOWN").upper(), "low")
            findings.append(
                {
                    "tool": "trivy",
                    "severity": sev,
                    "rule": vuln.get("VulnerabilityID", ""),
                    "title": vuln.get("Title") or f"CVE dans {vuln.get('PkgName', '?')}",
                    "message": (vuln.get("Description") or "")[:300],
                    "file": target,
                    "line": None,
                    "confidence": "high",
                    "fix_versions": [vuln["FixedVersion"]] if vuln.get("FixedVersion") else [],
                }
            )
    return findings


def _run_pip_audit(repo_dir: str) -> list[dict]:
    """Run pip-audit on requirements.txt / pyproject.toml if present."""
    dep_files = []
    for name in ("requirements.txt", "requirements-prod.txt", "requirements/base.txt"):
        if os.path.isfile(os.path.join(repo_dir, name)):
            dep_files.append(name)
            break

    if not dep_files:
        logger.info("pip-audit: no requirements file found, skipping")
        return []

    req_file = dep_files[0]
    data = base._run_json_tool(
        ["pip-audit", "-r", req_file, "-f", "json", "--no-deps"],
        repo_dir,
        "pip-audit",
    )
    if data is None:
        return []

    findings = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            aliases = vuln.get("aliases", [])
            severity = "high"
            findings.append(
                {
                    "tool": "pip-audit",
                    "severity": severity,
                    "rule": vuln.get("id", ""),
                    "title": f"CVE dans {dep.get('name', '?')} {dep.get('version', '')}",
                    "message": vuln.get("description", aliases[0] if aliases else ""),
                    "file": req_file,
                    "line": None,
                    "confidence": "high",
                    "fix_versions": vuln.get("fix_versions", []),
                }
            )
    return findings


def _run_osv_scanner(repo_dir: str) -> list[dict]:
    """Run Google OSV-Scanner for multi-ecosystem vulnerability detection."""
    code, stdout, stderr = base._run(
        ["osv-scanner", "--format", "json", "--recursive", "."],
        cwd=repo_dir,
        timeout=180,
    )
    raw = stdout or stderr
    if not raw:
        logger.warning("osv-scanner produced no output")
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"osv-scanner JSON parse error: {raw[:200]}")
        return []

    severity_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
    }
    findings = []
    for result in data.get("results", []):
        source_path = result.get("source", {}).get("path", "")
        for pkg in result.get("packages", []):
            pkg_name = pkg.get("package", {}).get("name", "?")
            pkg_version = pkg.get("package", {}).get("version", "")
            for vuln in pkg.get("vulnerabilities", []):
                sev = "medium"
                for s in vuln.get("severity", []):
                    sev = severity_map.get(s.get("score", "").upper()[:8], sev)
                    break
                aliases = vuln.get("aliases", [])
                cve = next((a for a in aliases if a.startswith("CVE-")), vuln.get("id", ""))
                findings.append(
                    {
                        "tool": "osv-scanner",
                        "severity": sev,
                        "rule": cve,
                        "title": f"{cve} dans {pkg_name} {pkg_version}",
                        "message": vuln.get("summary", vuln.get("details", ""))[:300],
                        "file": source_path.replace(repo_dir, "").lstrip("/\\") or "lockfile",
                        "line": None,
                        "confidence": "high",
                        "fix_versions": [],
                    }
                )
    return findings


def _run_safety(repo_dir: str) -> list[dict]:
    """Run safety to check Python deps against the PyUp advisory database."""
    req_path = None
    for name in ("requirements.txt", "requirements-prod.txt", "requirements/base.txt"):
        candidate = os.path.join(repo_dir, name)
        if os.path.isfile(candidate):
            req_path = (name, candidate)
            break
    if not req_path:
        logger.info("safety: no requirements file found, skipping")
        return []

    req_name, req_file = req_path
    code, stdout, stderr = base._run(
        ["safety", "check", "-r", req_file, "--json"],
        cwd=repo_dir,
        timeout=120,
    )
    raw = stdout or stderr
    if not raw:
        logger.warning(f"safety produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"safety JSON parse error: {raw[:200]}")
        return []

    findings = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, list) or len(item) < 5:
            continue
        findings.append(
            {
                "tool": "safety",
                "severity": "high",
                "rule": str(item[4]),
                "title": f"Vulnérabilité dans {item[0]} {item[2]}",
                "message": str(item[3])[:300],
                "file": req_name,
                "line": None,
                "confidence": "high",
                "fix_versions": [],
            }
        )
    return findings


def _run_grype(repo_dir: str) -> list[dict]:
    """Run grype for multi-ecosystem CVE scanning (pip, npm, go, cargo, …)."""
    code, stdout, stderr = base._run(
        ["grype", f"dir:{repo_dir}", "-o", "json", "--quiet"],
        cwd=repo_dir,
        timeout=300,
    )
    if not stdout:
        logger.warning(f"grype produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"grype JSON parse error: {stdout[:200]}")
        return []

    severity_map = {
        "Critical": "critical",
        "High": "high",
        "Medium": "medium",
        "Low": "low",
        "Negligible": "low",
        "Unknown": "low",
    }
    findings = []
    for match in data.get("matches", []):
        vuln = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        sev = severity_map.get(vuln.get("severity", "Unknown"), "low")
        fix = vuln.get("fix", {})
        fix_versions = fix.get("versions", []) if isinstance(fix, dict) else []
        locations = artifact.get("locations", [])
        file_path = locations[0].get("path", "").lstrip("/\\") if locations else ""
        findings.append(
            {
                "tool": "grype",
                "severity": sev,
                "rule": vuln.get("id", ""),
                "title": f"{vuln.get('id', '?')} dans {artifact.get('name', '?')} {artifact.get('version', '')}",
                "message": (vuln.get("description") or "")[:300],
                "file": file_path,
                "line": None,
                "confidence": "high",
                "fix_versions": fix_versions,
            }
        )
    return findings
