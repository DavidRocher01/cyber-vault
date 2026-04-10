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


# ─── severity counters ────────────────────────────────────────────────────────

def _count_severities(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "low")
        if sev in counts:
            counts[sev] += 1
    return counts


# ─── main entry point ─────────────────────────────────────────────────────────

async def run_code_scan(scan_id: int, db: AsyncSession) -> None:
    """
    Background task: clone repo, run tools, persist results.
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
        logger.info(f"CodeScan {scan_id}: cloning {scan.repo_url}")
        clone_url = scan.repo_url  # token already embedded if provided
        rc, _, stderr = _run(
            ["git", "clone", "--depth=1", clone_url, "repo"],
            cwd=tmp_dir,
            timeout=120,
        )
        if rc != 0:
            raise RuntimeError(f"git clone failed: {stderr[:300]}")

        repo_dir = os.path.join(tmp_dir, "repo")

        # ── Run tools ──────────────────────────────────────────────────────
        all_findings: list[dict] = []

        logger.info(f"CodeScan {scan_id}: running Bandit")
        all_findings.extend(_run_bandit(repo_dir))

        logger.info(f"CodeScan {scan_id}: running Semgrep")
        all_findings.extend(_run_semgrep(repo_dir))

        logger.info(f"CodeScan {scan_id}: running pip-audit")
        all_findings.extend(_run_pip_audit(repo_dir))

        logger.info(f"CodeScan {scan_id}: running gitleaks")
        all_findings.extend(_run_gitleaks(repo_dir))

        logger.info(f"CodeScan {scan_id}: running detect-secrets")
        all_findings.extend(_run_detect_secrets(repo_dir))

        logger.info(f"CodeScan {scan_id}: running npm audit")
        all_findings.extend(_run_npm_audit(repo_dir))

        logger.info(f"CodeScan {scan_id}: running trivy")
        all_findings.extend(_run_trivy(repo_dir))

        logger.info(f"CodeScan {scan_id}: running checkov")
        all_findings.extend(_run_checkov(repo_dir))

        # ── Aggregate ──────────────────────────────────────────────────────
        counts = _count_severities(all_findings)
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

        all_findings: list[dict] = []
        logger.info(f"CodeScan {scan_id}: running Bandit")
        all_findings.extend(_run_bandit(repo_dir))
        logger.info(f"CodeScan {scan_id}: running Semgrep")
        all_findings.extend(_run_semgrep(repo_dir))
        logger.info(f"CodeScan {scan_id}: running pip-audit")
        all_findings.extend(_run_pip_audit(repo_dir))
        logger.info(f"CodeScan {scan_id}: running gitleaks")
        all_findings.extend(_run_gitleaks(repo_dir))
        logger.info(f"CodeScan {scan_id}: running detect-secrets")
        all_findings.extend(_run_detect_secrets(repo_dir))
        logger.info(f"CodeScan {scan_id}: running npm audit")
        all_findings.extend(_run_npm_audit(repo_dir))
        logger.info(f"CodeScan {scan_id}: running trivy")
        all_findings.extend(_run_trivy(repo_dir))
        logger.info(f"CodeScan {scan_id}: running checkov")
        all_findings.extend(_run_checkov(repo_dir))

        counts = _count_severities(all_findings)
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
