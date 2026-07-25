"""
iac.py — infrastructure-as-code misconfiguration runners.

checkov (Dockerfile / k8s / Terraform / …), hadolint (Dockerfile best-practices),
tfsec (Terraform security). Each returns a list of normalised finding dicts.
"""

from __future__ import annotations

import json
import os

from loguru import logger

from . import base


def _run_checkov(repo_dir: str) -> list[dict]:
    """Run checkov to detect IaC misconfigurations (Dockerfile, k8s, Terraform, …)."""
    code, stdout, stderr = base._run(
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
            findings.append(
                {
                    "tool": "checkov",
                    "severity": sev,
                    "rule": check_id,
                    "title": check_name,
                    "message": f"Échec de la règle {check_id} sur {check.get('resource', '?')}",
                    "file": (check.get("file_path") or "").lstrip("/\\"),
                    "line": (check.get("file_line_range") or [None])[0],
                    "confidence": "high",
                }
            )
    return findings


def _run_hadolint(repo_dir: str) -> list[dict]:
    """Run hadolint on Dockerfile(s) for best-practice and security checks."""
    import glob as _glob

    dockerfiles = _glob.glob(os.path.join(repo_dir, "**/Dockerfile"), recursive=True) + _glob.glob(
        os.path.join(repo_dir, "**/Dockerfile.*"), recursive=True
    )
    if not dockerfiles:
        logger.info("hadolint: no Dockerfile found, skipping")
        return []

    severity_map = {"error": "high", "warning": "medium", "info": "low", "style": "low"}
    findings = []
    for dockerfile in dockerfiles[:5]:
        code, stdout, stderr = base._run(
            ["hadolint", "-f", "json", dockerfile], cwd=repo_dir, timeout=30
        )
        raw = stdout or stderr
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        for issue in data if isinstance(data, list) else []:
            sev = severity_map.get(issue.get("level", "warning").lower(), "medium")
            findings.append(
                {
                    "tool": "hadolint",
                    "severity": sev,
                    "rule": issue.get("code", ""),
                    "title": issue.get("code", "Hadolint"),
                    "message": issue.get("message", ""),
                    "file": (issue.get("file") or dockerfile).replace(repo_dir, "").lstrip("/\\"),
                    "line": issue.get("line"),
                    "confidence": "high",
                }
            )
    return findings


def _run_tfsec(repo_dir: str) -> list[dict]:
    """Run tfsec on Terraform files for security misconfigurations."""
    import glob as _glob

    if not _glob.glob(os.path.join(repo_dir, "**/*.tf"), recursive=True):
        logger.info("tfsec: no .tf files found, skipping")
        return []

    code, stdout, stderr = base._run(
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

    severity_map = {
        "CRITICAL": "critical",
        "HIGH": "high",
        "MEDIUM": "medium",
        "LOW": "low",
    }
    findings = []
    for result in data.get("results", []) or []:
        sev = severity_map.get(result.get("severity", "MEDIUM").upper(), "medium")
        loc = result.get("location", {})
        findings.append(
            {
                "tool": "tfsec",
                "severity": sev,
                "rule": result.get("rule_id", result.get("long_id", "")),
                "title": result.get("description", result.get("rule_description", "")),
                "message": (
                    result.get("impact", "")
                    + (" — " + result.get("resolution", "") if result.get("resolution") else "")
                ),
                "file": (loc.get("filename") or "").replace(repo_dir, "").lstrip("/\\"),
                "line": loc.get("start_line"),
                "confidence": "high",
            }
        )
    return findings
