"""
Code security analysis service.

Clones a Git repository into a temporary directory and runs:
  - Bandit  (Python SAST)
  - Semgrep (multi-language SAST)
  - pip-audit (dependency CVE audit)

Results are stored as JSON in the code_scans table.
"""

import asyncio
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_scan import CodeScan


# ─── helpers ──────────────────────────────────────────────────────────────────

def _sanitize_repo_url(url: str, token: str | None) -> str:
    """Inject a PAT token into https:// URLs if provided."""
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        return parsed._replace(netloc=f"{token}@{parsed.netloc}").geturl()
    return url


def _extract_repo_name(url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    url = url.rstrip("/").rstrip(".git")
    parts = url.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1]


def _run(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout, stderr)."""
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout after {timeout}s"
    except FileNotFoundError:
        return 1, "", f"Command not found: {cmd[0]}"


# ─── individual tool runners ──────────────────────────────────────────────────

def _run_bandit(repo_dir: str) -> list[dict]:
    """Run Bandit on all Python files. Returns list of findings."""
    code, stdout, stderr = _run(
        ["bandit", "-r", ".", "-f", "json", "-q", "--exit-zero"],
        cwd=repo_dir,
    )
    if not stdout:
        logger.warning(f"Bandit produced no output: {stderr}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"Bandit JSON parse error: {stdout[:200]}")
        return []

    findings = []
    for issue in data.get("results", []):
        # Bandit severities: HIGH, MEDIUM, LOW → map to our levels
        sev_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
        severity = sev_map.get(issue.get("issue_severity", "").upper(), "low")
        findings.append({
            "tool": "bandit",
            "severity": severity,
            "rule": issue.get("test_id", ""),
            "title": issue.get("test_name", ""),
            "message": issue.get("issue_text", ""),
            "file": issue.get("filename", "").replace(repo_dir, "").lstrip("/\\"),
            "line": issue.get("line_number"),
            "confidence": issue.get("issue_confidence", ""),
        })
    return findings


def _run_semgrep(repo_dir: str) -> list[dict]:
    """Run Semgrep with the auto ruleset. Returns list of findings."""
    code, stdout, stderr = _run(
        ["semgrep", "scan", "--config=auto", "--json", "--quiet", "--timeout=60"],
        cwd=repo_dir,
        timeout=180,
    )
    if not stdout:
        logger.warning(f"Semgrep produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"Semgrep JSON parse error: {stdout[:200]}")
        return []

    severity_map = {
        "ERROR": "high",
        "WARNING": "medium",
        "INFO": "low",
    }
    findings = []
    for r in data.get("results", []):
        extra = r.get("extra", {})
        sev_raw = extra.get("severity", extra.get("metadata", {}).get("severity", "INFO")).upper()
        # Some rules expose CRITICAL
        if sev_raw == "CRITICAL":
            severity = "critical"
        else:
            severity = severity_map.get(sev_raw, "low")

        findings.append({
            "tool": "semgrep",
            "severity": severity,
            "rule": r.get("check_id", ""),
            "title": r.get("check_id", "").split(".")[-1].replace("-", " ").title(),
            "message": extra.get("message", ""),
            "file": r.get("path", "").replace(repo_dir, "").lstrip("/\\"),
            "line": r.get("start", {}).get("line"),
            "confidence": "",
        })
    return findings


def _run_gitleaks(repo_dir: str) -> list[dict]:
    """Run gitleaks to detect hardcoded secrets and credentials."""
    report_file = "gitleaks-report.json"
    report_path = os.path.join(repo_dir, report_file)
    _run(
        [
            "gitleaks", "detect", "--source", ".",
            "--no-git",
            "--report-format", "json",
            "--report-path", report_file,
            "--exit-code", "0",
        ],
        cwd=repo_dir,
        timeout=120,
    )
    if not os.path.isfile(report_path):
        return []
    try:
        with open(report_path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"gitleaks report parse error: {e}")
        return []

    if not isinstance(data, list):
        return []

    findings = []
    for leak in data:
        match_preview = (leak.get("Match") or "")[:80]
        findings.append({
            "tool": "gitleaks",
            "severity": "critical",
            "rule": leak.get("RuleID", ""),
            "title": leak.get("Description", "Secret détecté"),
            "message": f"Secret potentiel : {match_preview}" if match_preview else "Secret potentiel détecté",
            "file": (leak.get("File") or "").replace(repo_dir, "").lstrip("/\\"),
            "line": leak.get("StartLine"),
            "confidence": "high",
        })
    return findings


def _run_npm_audit(repo_dir: str) -> list[dict]:
    """Run npm audit if package.json is present. Supports npm 7+ JSON v2 format."""
    if not os.path.isfile(os.path.join(repo_dir, "package.json")):
        logger.info("npm audit: no package.json found, skipping")
        return []

    # Generate lock file without installing if missing
    if not os.path.isfile(os.path.join(repo_dir, "package-lock.json")):
        logger.info("npm audit: generating package-lock.json")
        _run(
            ["npm", "install", "--package-lock-only", "--ignore-scripts", "--no-audit"],
            cwd=repo_dir,
            timeout=120,
        )

    _code, stdout, stderr = _run(
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
    # npm 7+ format: data["vulnerabilities"] is a dict keyed by package name
    for pkg_name, vuln in data.get("vulnerabilities", {}).items():
        via = vuln.get("via", [])
        advisories = [v for v in via if isinstance(v, dict)]
        if advisories:
            for adv in advisories:
                sev = severity_map.get(adv.get("severity", vuln.get("severity", "low")), "low")
                findings.append({
                    "tool": "npm-audit",
                    "severity": sev,
                    "rule": str(adv.get("source", "")),
                    "title": adv.get("title", f"Vulnérabilité dans {pkg_name}"),
                    "message": adv.get("url", adv.get("title", "")),
                    "file": "package.json",
                    "line": None,
                    "confidence": "high",
                    "fix_versions": [],
                })
        else:
            sev = severity_map.get(vuln.get("severity", "low"), "low")
            findings.append({
                "tool": "npm-audit",
                "severity": sev,
                "rule": "",
                "title": f"Vulnérabilité dans {pkg_name}",
                "message": f"Paquet affecté : {pkg_name} ({vuln.get('range', '')})",
                "file": "package.json",
                "line": None,
                "confidence": "high",
                "fix_versions": [],
            })
    return findings


def _run_detect_secrets(repo_dir: str) -> list[dict]:
    """Run detect-secrets to find potential secrets with entropy analysis."""
    code, stdout, stderr = _run(
        ["detect-secrets", "scan", "."],
        cwd=repo_dir,
        timeout=120,
    )
    if not stdout:
        logger.warning(f"detect-secrets produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"detect-secrets JSON parse error: {stdout[:200]}")
        return []

    findings = []
    for file_path, secrets in data.get("results", {}).items():
        for secret in secrets:
            findings.append({
                "tool": "detect-secrets",
                "severity": "critical",
                "rule": secret.get("type", ""),
                "title": secret.get("type", "Secret potentiel"),
                "message": f"Secret potentiel à la ligne {secret.get('line_number', '?')} (non vérifié)",
                "file": file_path.replace(repo_dir, "").lstrip("/\\"),
                "line": secret.get("line_number"),
                "confidence": "medium",
            })
    return findings


def _run_trivy(repo_dir: str) -> list[dict]:
    """Run trivy fs for multi-ecosystem CVE detection (pip, npm, go, cargo, …)."""
    code, stdout, stderr = _run(
        ["trivy", "fs", ".", "--format", "json", "--quiet", "--no-progress"],
        cwd=repo_dir,
        timeout=180,
    )
    if not stdout:
        logger.warning(f"trivy produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"trivy JSON parse error: {stdout[:200]}")
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
            findings.append({
                "tool": "trivy",
                "severity": sev,
                "rule": vuln.get("VulnerabilityID", ""),
                "title": vuln.get("Title") or f"CVE dans {vuln.get('PkgName', '?')}",
                "message": (vuln.get("Description") or "")[:300],
                "file": target,
                "line": None,
                "confidence": "high",
                "fix_versions": [vuln["FixedVersion"]] if vuln.get("FixedVersion") else [],
            })
    return findings


def _run_checkov(repo_dir: str) -> list[dict]:
    """Run checkov to detect IaC misconfigurations (Dockerfile, k8s, Terraform, …)."""
    code, stdout, stderr = _run(
        ["checkov", "-d", ".", "--output", "json", "--quiet", "--compact"],
        cwd=repo_dir,
        timeout=180,
    )
    if not stdout:
        logger.warning(f"checkov produced no output: {stderr[:300]}")
        return []
    try:
        raw = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"checkov JSON parse error: {stdout[:200]}")
        return []

    severity_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
    }

    # checkov may return a single dict or a list when multiple frameworks are scanned
    results_list = raw if isinstance(raw, list) else [raw]

    findings = []
    for block in results_list:
        failed = block.get("results", {}).get("failed_checks", [])
        for check in failed:
            sev_raw = (check.get("severity") or "MEDIUM").upper()
            sev = severity_map.get(sev_raw, "medium")
            check_meta = check.get("check", {}) if isinstance(check.get("check"), dict) else {}
            check_id = check.get("check_id", check_meta.get("id", ""))
            check_name = check_meta.get("name", check_id)
            findings.append({
                "tool": "checkov",
                "severity": sev,
                "rule": check_id,
                "title": check_name,
                "message": f"Échec de la règle {check_id} sur {check.get('resource', '?')}",
                "file": (check.get("file_path") or "").lstrip("/\\"),
                "line": (check.get("file_line_range") or [None])[0],
                "confidence": "high",
            })
    return findings


def _run_pip_audit(repo_dir: str) -> list[dict]:
    """
    Run pip-audit on requirements.txt / pyproject.toml if present.
    Returns list of findings.
    """
    # Find dependency files
    dep_files = []
    for name in ("requirements.txt", "requirements-prod.txt", "requirements/base.txt"):
        if os.path.isfile(os.path.join(repo_dir, name)):
            dep_files.append(name)
            break  # audit first found

    if not dep_files:
        logger.info("pip-audit: no requirements file found, skipping")
        return []

    req_file = dep_files[0]
    code, stdout, stderr = _run(
        ["pip-audit", "-r", req_file, "-f", "json", "--no-deps"],
        cwd=repo_dir,
    )
    if not stdout:
        logger.warning(f"pip-audit produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"pip-audit JSON parse error: {stdout[:200]}")
        return []

    findings = []
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            # CVSS score → severity
            cvss = vuln.get("fix_versions") and 0  # no CVSS in basic output
            aliases = vuln.get("aliases", [])
            severity = "high"  # default for known CVEs
            findings.append({
                "tool": "pip-audit",
                "severity": severity,
                "rule": vuln.get("id", ""),
                "title": f"CVE dans {dep.get('name', '?')} {dep.get('version', '')}",
                "message": vuln.get("description", aliases[0] if aliases else ""),
                "file": req_file,
                "line": None,
                "confidence": "high",
                "fix_versions": vuln.get("fix_versions", []),
            })
    return findings


def _run_trufflehog(repo_dir: str) -> list[dict]:
    """Scan filesystem for secrets using trufflehog (entropy + pattern matching)."""
    code, stdout, stderr = _run(
        ["trufflehog", "filesystem", ".", "--json", "--no-update"],
        cwd=repo_dir,
        timeout=180,
    )
    if not stdout:
        logger.warning(f"trufflehog produced no output: {stderr[:300]}")
        return []
    findings = []
    for line in stdout.strip().splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        det = item.get("DetectorName", "secret")
        raw = item.get("Raw", "") or item.get("RawV2", "")
        preview = (raw[:60] + "…") if len(raw) > 60 else raw
        source = item.get("SourceMetadata", {}).get("Data", {})
        file_path, line_num = "", None
        for v in source.values():
            if isinstance(v, dict):
                file_path = v.get("file", "")
                line_num = v.get("line")
                break
        findings.append({
            "tool": "trufflehog",
            "severity": "critical",
            "rule": det,
            "title": f"Secret détecté : {det}",
            "message": f"Valeur : {preview}" if preview else "Secret potentiel détecté",
            "file": file_path.lstrip("/\\"),
            "line": line_num,
            "confidence": "high" if item.get("Verified") else "medium",
        })
    return findings


def _run_njsscan(repo_dir: str) -> list[dict]:
    """Run njsscan for Node.js / JavaScript SAST."""
    code, stdout, stderr = _run(
        ["njsscan", "--json", "-o", "-", "."],
        cwd=repo_dir,
        timeout=120,
    )
    if not stdout:
        logger.warning(f"njsscan produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"njsscan JSON parse error: {stdout[:200]}")
        return []

    severity_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
    findings = []
    for section in ("nodejs", "templates"):
        for rule_id, rule_data in (data.get(section) or {}).items():
            if not isinstance(rule_data, dict):
                continue
            sev = severity_map.get(rule_data.get("metadata", {}).get("severity", "WARNING").upper(), "medium")
            for match in rule_data.get("files", []):
                findings.append({
                    "tool": "njsscan",
                    "severity": sev,
                    "rule": rule_id,
                    "title": rule_data.get("metadata", {}).get("description", rule_id),
                    "message": rule_data.get("metadata", {}).get("description", ""),
                    "file": match.get("file_path", "").lstrip("/\\"),
                    "line": (match.get("match_lines") or [None])[0],
                    "confidence": "",
                })
    return findings


def _run_bearer(repo_dir: str) -> list[dict]:
    """Run Bearer to detect PII leaks and data-security issues."""
    code, stdout, stderr = _run(
        ["bearer", "scan", ".", "--format", "json", "--quiet"],
        cwd=repo_dir,
        timeout=300,
    )
    raw = stdout or stderr
    if not raw:
        logger.warning("bearer produced no output")
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"bearer JSON parse error: {raw[:200]}")
        return []

    severity_map = {"critical": "critical", "high": "high", "medium": "medium", "low": "low", "warning": "medium"}
    findings = []
    for sev_key, items in data.items():
        if not isinstance(items, list):
            continue
        sev = severity_map.get(sev_key.lower(), "medium")
        for item in items:
            findings.append({
                "tool": "bearer",
                "severity": sev,
                "rule": item.get("rule_id", ""),
                "title": item.get("title", item.get("rule_id", "Bearer finding")),
                "message": item.get("description", item.get("detail", ""))[:300],
                "file": (item.get("filename") or "").lstrip("/\\"),
                "line": item.get("line_number"),
                "confidence": "high",
            })
    return findings


def _run_gosec(repo_dir: str) -> list[dict]:
    """Run gosec for Go source security analysis."""
    import glob as _glob
    if not _glob.glob(os.path.join(repo_dir, "**/*.go"), recursive=True):
        logger.info("gosec: no .go files found, skipping")
        return []
    code, stdout, stderr = _run(
        ["gosec", "-fmt", "json", "-stdout", "-quiet", "./..."],
        cwd=repo_dir,
        timeout=180,
    )
    if not stdout:
        logger.warning(f"gosec produced no output: {stderr[:300]}")
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"gosec JSON parse error: {stdout[:200]}")
        return []

    severity_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    findings = []
    for issue in data.get("Issues", []) or []:
        sev = severity_map.get(issue.get("severity", "LOW").upper(), "low")
        findings.append({
            "tool": "gosec",
            "severity": sev,
            "rule": issue.get("rule_id", ""),
            "title": issue.get("details", issue.get("rule_id", "")),
            "message": f"{issue.get('details', '')} (confidence: {issue.get('confidence', '')})",
            "file": (issue.get("file") or "").replace(repo_dir, "").lstrip("/\\"),
            "line": issue.get("line"),
            "confidence": issue.get("confidence", ""),
        })
    return findings


def _run_eslint_security(repo_dir: str) -> list[dict]:
    """Run eslint with eslint-plugin-security on JS/TS files."""
    import glob as _glob
    js_files = [
        f for ext in ("*.js", "*.ts", "*.jsx", "*.tsx")
        for f in _glob.glob(os.path.join(repo_dir, "**", ext), recursive=True)
        if "node_modules" not in f
    ]
    if not js_files:
        logger.info("eslint-security: no JS/TS files found, skipping")
        return []

    eslint_config = os.path.join(repo_dir, ".eslintrc-cyberscan.json")
    with open(eslint_config, "w") as f:
        json.dump({
            "plugins": ["security"],
            "rules": {
                "security/detect-unsafe-regex": "error",
                "security/detect-buffer-noassert": "error",
                "security/detect-child-process": "warn",
                "security/detect-disable-mustache-escape": "error",
                "security/detect-eval-with-expression": "error",
                "security/detect-new-buffer": "warn",
                "security/detect-no-csrf-before-method-override": "error",
                "security/detect-non-literal-fs-filename": "warn",
                "security/detect-non-literal-regexp": "warn",
                "security/detect-non-literal-require": "warn",
                "security/detect-object-injection": "warn",
                "security/detect-possible-timing-attacks": "warn",
                "security/detect-pseudoRandomBytes": "error",
            },
        }, f)

    code, stdout, _ = _run(
        ["eslint", "--config", eslint_config, "--format", "json",
         "--no-eslintrc", "--ext", ".js,.ts,.jsx,.tsx", "."],
        cwd=repo_dir,
        timeout=120,
    )
    try:
        os.unlink(eslint_config)
    except OSError:
        pass

    if not stdout:
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []

    severity_map = {1: "medium", 2: "high"}
    findings = []
    for file_result in data:
        rel_path = file_result.get("filePath", "").replace(repo_dir, "").lstrip("/\\")
        for msg in file_result.get("messages", []):
            sev = severity_map.get(msg.get("severity", 1), "medium")
            rule = msg.get("ruleId", "")
            findings.append({
                "tool": "eslint-security",
                "severity": sev,
                "rule": rule,
                "title": rule.replace("security/", "").replace("-", " ").title() if rule else "ESLint security",
                "message": msg.get("message", ""),
                "file": rel_path,
                "line": msg.get("line"),
                "confidence": "",
            })
    return findings


def _run_osv_scanner(repo_dir: str) -> list[dict]:
    """Run Google OSV-Scanner for multi-ecosystem vulnerability detection."""
    code, stdout, stderr = _run(
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

    severity_map = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
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
                findings.append({
                    "tool": "osv-scanner",
                    "severity": sev,
                    "rule": cve,
                    "title": f"{cve} dans {pkg_name} {pkg_version}",
                    "message": vuln.get("summary", vuln.get("details", ""))[:300],
                    "file": source_path.replace(repo_dir, "").lstrip("/\\") or "lockfile",
                    "line": None,
                    "confidence": "high",
                    "fix_versions": [],
                })
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
    code, stdout, stderr = _run(
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

    # safety 2.x format: list of [pkg, spec, installed, advisory, vuln_id]
    findings = []
    for item in data if isinstance(data, list) else []:
        if not isinstance(item, list) or len(item) < 5:
            continue
        findings.append({
            "tool": "safety",
            "severity": "high",
            "rule": str(item[4]),
            "title": f"Vulnérabilité dans {item[0]} {item[2]}",
            "message": str(item[3])[:300],
            "file": req_name,
            "line": None,
            "confidence": "high",
            "fix_versions": [],
        })
    return findings


def _run_hadolint(repo_dir: str) -> list[dict]:
    """Run hadolint on Dockerfile(s) for best-practice and security checks."""
    import glob as _glob
    dockerfiles = (
        _glob.glob(os.path.join(repo_dir, "**/Dockerfile"), recursive=True) +
        _glob.glob(os.path.join(repo_dir, "**/Dockerfile.*"), recursive=True)
    )
    if not dockerfiles:
        logger.info("hadolint: no Dockerfile found, skipping")
        return []

    severity_map = {"error": "high", "warning": "medium", "info": "low", "style": "low"}
    findings = []
    for dockerfile in dockerfiles[:5]:
        code, stdout, stderr = _run(["hadolint", "-f", "json", dockerfile], cwd=repo_dir, timeout=30)
        raw = stdout or stderr
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for issue in data if isinstance(data, list) else []:
            sev = severity_map.get(issue.get("level", "warning").lower(), "medium")
            findings.append({
                "tool": "hadolint",
                "severity": sev,
                "rule": issue.get("code", ""),
                "title": issue.get("code", "Hadolint"),
                "message": issue.get("message", ""),
                "file": (issue.get("file") or dockerfile).replace(repo_dir, "").lstrip("/\\"),
                "line": issue.get("line"),
                "confidence": "high",
            })
    return findings


def _run_tfsec(repo_dir: str) -> list[dict]:
    """Run tfsec on Terraform files for security misconfigurations."""
    import glob as _glob
    if not _glob.glob(os.path.join(repo_dir, "**/*.tf"), recursive=True):
        logger.info("tfsec: no .tf files found, skipping")
        return []

    code, stdout, stderr = _run(
        ["tfsec", ".", "--format", "json", "--no-color", "--soft-fail"],
        cwd=repo_dir,
        timeout=120,
    )
    raw = stdout or stderr
    if not raw:
        logger.warning("tfsec produced no output")
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning(f"tfsec JSON parse error: {raw[:200]}")
        return []

    severity_map = {"CRITICAL": "critical", "HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    findings = []
    for result in data.get("results", []) or []:
        sev = severity_map.get(result.get("severity", "MEDIUM").upper(), "medium")
        loc = result.get("location", {})
        findings.append({
            "tool": "tfsec",
            "severity": sev,
            "rule": result.get("rule_id", result.get("long_id", "")),
            "title": result.get("description", result.get("rule_description", "")),
            "message": (result.get("impact", "") + (" — " + result.get("resolution", "") if result.get("resolution") else "")),
            "file": (loc.get("filename") or "").replace(repo_dir, "").lstrip("/\\"),
            "line": loc.get("start_line"),
            "confidence": "high",
        })
    return findings


def _run_grype(repo_dir: str) -> list[dict]:
    """Run grype for multi-ecosystem CVE scanning (pip, npm, go, cargo, …)."""
    code, stdout, stderr = _run(
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

    severity_map = {"Critical": "critical", "High": "high", "Medium": "medium", "Low": "low", "Negligible": "low", "Unknown": "low"}
    findings = []
    for match in data.get("matches", []):
        vuln = match.get("vulnerability", {})
        artifact = match.get("artifact", {})
        sev = severity_map.get(vuln.get("severity", "Unknown"), "low")
        fix = vuln.get("fix", {})
        fix_versions = fix.get("versions", []) if isinstance(fix, dict) else []
        locations = artifact.get("locations", [])
        file_path = locations[0].get("path", "").lstrip("/\\") if locations else ""
        findings.append({
            "tool": "grype",
            "severity": sev,
            "rule": vuln.get("id", ""),
            "title": f"{vuln.get('id', '?')} dans {artifact.get('name', '?')} {artifact.get('version', '')}",
            "message": (vuln.get("description") or "")[:300],
            "file": file_path,
            "line": None,
            "confidence": "high",
            "fix_versions": fix_versions,
        })
    return findings


# ─── severity counters ────────────────────────────────────────────────────────

def _count_severities(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "low")
        if sev in counts:
            counts[sev] += 1
    return counts


# ─── shared tool runner ───────────────────────────────────────────────────────

def _run_all_tools(scan_id: int, repo_dir: str) -> tuple[list[dict], dict]:
    """Run every security tool on repo_dir. Returns (all_findings, severity_counts)."""
    all_findings: list[dict] = []
    for name, runner in [
        ("Bandit",          _run_bandit),
        ("Semgrep",         _run_semgrep),
        ("pip-audit",       _run_pip_audit),
        ("gitleaks",        _run_gitleaks),
        ("trufflehog",      _run_trufflehog),
        ("detect-secrets",  _run_detect_secrets),
        ("npm audit",       _run_npm_audit),
        ("njsscan",         _run_njsscan),
        ("eslint-security", _run_eslint_security),
        ("trivy",           _run_trivy),
        ("grype",           _run_grype),
        ("osv-scanner",     _run_osv_scanner),
        ("safety",          _run_safety),
        ("checkov",         _run_checkov),
        ("hadolint",        _run_hadolint),
        ("tfsec",           _run_tfsec),
        ("gosec",           _run_gosec),
        ("bearer",          _run_bearer),
    ]:
        logger.info(f"CodeScan {scan_id}: running {name}")
        all_findings.extend(runner(repo_dir))
    return all_findings, _count_severities(all_findings)


# ─── main entry points ────────────────────────────────────────────────────────

async def run_code_scan(scan_id: int, db: AsyncSession, clone_url: str | None = None) -> None:
    """
    Background task: clone repo, run tools, persist results.
    clone_url — URL with embedded token if provided; never stored in DB.
    """
    from sqlalchemy import select

    result = await db.execute(select(CodeScan).where(CodeScan.id == scan_id))
    scan: CodeScan | None = result.scalar_one_or_none()
    if not scan:
        logger.error(f"CodeScan {scan_id} not found")
        return

    scan.status = "running"
    scan.started_at = datetime.now(timezone.utc)
    await db.commit()

    tmp_dir = tempfile.mkdtemp(prefix="cyberscan_code_")
    try:
        # ── Clone ──────────────────────────────────────────────────────────
        effective_clone_url = clone_url or scan.repo_url
        logger.info(f"CodeScan {scan_id}: cloning {scan.repo_url}")
        rc, _, stderr = _run(
            ["git", "clone", "--depth=1", effective_clone_url, "repo"],
            cwd=tmp_dir,
            timeout=120,
        )
        if rc != 0:
            raise RuntimeError(f"git clone failed: {stderr[:300]}")

        repo_dir = os.path.join(tmp_dir, "repo")

        # ── Run all tools ──────────────────────────────────────────────────
        all_findings, counts = _run_all_tools(scan_id, repo_dir)
        total = sum(counts.values())

        results = {
            "findings": all_findings,
            "summary": {
                "total": total,
                **counts,
            },
        }

        scan.status = "done"
        scan.critical_count = counts["critical"]
        scan.high_count = counts["high"]
        scan.medium_count = counts["medium"]
        scan.low_count = counts["low"]
        scan.results_json = json.dumps(results)
        scan.finished_at = datetime.now(timezone.utc)
        logger.info(f"CodeScan {scan_id}: done — {total} findings")

    except Exception as exc:
        logger.exception(f"CodeScan {scan_id} failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:512]
        scan.finished_at = datetime.now(timezone.utc)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        await db.commit()


async def run_code_scan_zip(scan_id: int, zip_path: str, db: AsyncSession) -> None:
    """Background task: extract ZIP archive, run tools, persist results."""
    from sqlalchemy import select

    result = await db.execute(select(CodeScan).where(CodeScan.id == scan_id))
    scan: CodeScan | None = result.scalar_one_or_none()
    if not scan:
        logger.error(f"CodeScan {scan_id} not found")
        return

    scan.status = "running"
    scan.started_at = datetime.now(timezone.utc)
    await db.commit()

    tmp_dir = tempfile.mkdtemp(prefix="cyberscan_code_")
    try:
        logger.info(f"CodeScan {scan_id}: extracting ZIP")
        repo_dir = os.path.join(tmp_dir, "repo")
        os.makedirs(repo_dir, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as z:
            # Zip-bomb guard
            total_size = sum(info.file_size for info in z.infolist())
            if total_size > 200 * 1024 * 1024:
                raise RuntimeError("Archive trop volumineuse après extraction (max 200 MB)")
            # Path-traversal guard
            real_repo = os.path.realpath(repo_dir)
            for member in z.infolist():
                dest = os.path.realpath(os.path.join(repo_dir, member.filename))
                if not dest.startswith(real_repo + os.sep) and dest != real_repo:
                    raise RuntimeError("Archive contient des chemins invalides (path traversal)")
            z.extractall(repo_dir)

        # If ZIP wraps a single top-level folder, descend into it
        entries = os.listdir(repo_dir)
        if len(entries) == 1 and os.path.isdir(os.path.join(repo_dir, entries[0])):
            repo_dir = os.path.join(repo_dir, entries[0])

        all_findings, counts = _run_all_tools(scan_id, repo_dir)
        total = sum(counts.values())
        results = {"findings": all_findings, "summary": {"total": total, **counts}}

        scan.status = "done"
        scan.critical_count = counts["critical"]
        scan.high_count = counts["high"]
        scan.medium_count = counts["medium"]
        scan.low_count = counts["low"]
        scan.results_json = json.dumps(results)
        scan.finished_at = datetime.now(timezone.utc)
        logger.info(f"CodeScan {scan_id}: done — {total} findings")

    except Exception as exc:
        logger.exception(f"CodeScan {scan_id} (ZIP) failed: {exc}")
        scan.status = "failed"
        scan.error_message = str(exc)[:512]
        scan.finished_at = datetime.now(timezone.utc)

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        try:
            os.unlink(zip_path)
        except Exception:
            pass
        await db.commit()
