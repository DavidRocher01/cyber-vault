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
