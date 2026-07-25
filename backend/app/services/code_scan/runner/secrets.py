"""
secrets.py — hardcoded-secret / credential detection runners.

gitleaks & trufflehog (pattern + entropy), detect-secrets (entropy analysis).
Each returns a list of normalised finding dicts; secrets are always reported at
``critical`` severity.
"""

from __future__ import annotations

import json
import os

from loguru import logger

from . import base


def _run_gitleaks(repo_dir: str) -> list[dict]:
    """Run gitleaks to detect hardcoded secrets and credentials."""
    report_file = "gitleaks-report.json"
    report_path = os.path.join(repo_dir, report_file)
    base._run(
        [
            "gitleaks",
            "detect",
            "--source",
            ".",
            "--no-git",
            "--report-format",
            "json",
            "--report-path",
            report_file,
            "--exit-code",
            "0",
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
        findings.append(
            {
                "tool": "gitleaks",
                "severity": "critical",
                "rule": leak.get("RuleID", ""),
                "title": leak.get("Description", "Secret détecté"),
                "message": f"Secret potentiel : {match_preview}"
                if match_preview
                else "Secret potentiel détecté",
                "file": (leak.get("File") or "").replace(repo_dir, "").lstrip("/\\"),
                "line": leak.get("StartLine"),
                "confidence": "high",
            }
        )
    return findings


def _run_detect_secrets(repo_dir: str) -> list[dict]:
    """Run detect-secrets to find potential secrets with entropy analysis."""
    data = base._run_json_tool(
        ["detect-secrets", "scan", "."],
        repo_dir,
        "detect-secrets",
        timeout=120,
    )
    if data is None:
        return []

    findings = []
    for file_path, secrets in data.get("results", {}).items():
        for secret in secrets:
            findings.append(
                {
                    "tool": "detect-secrets",
                    "severity": "critical",
                    "rule": secret.get("type", ""),
                    "title": secret.get("type", "Secret potentiel"),
                    "message": f"Secret potentiel à la ligne {secret.get('line_number', '?')} (non vérifié)",
                    "file": file_path.replace(repo_dir, "").lstrip("/\\"),
                    "line": secret.get("line_number"),
                    "confidence": "medium",
                }
            )
    return findings


def _run_trufflehog(repo_dir: str) -> list[dict]:
    """Scan filesystem for secrets using trufflehog (entropy + pattern matching)."""
    code, stdout, stderr = base._run(
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
        findings.append(
            {
                "tool": "trufflehog",
                "severity": "critical",
                "rule": det,
                "title": f"Secret détecté : {det}",
                "message": f"Valeur : {preview}" if preview else "Secret potentiel détecté",
                "file": file_path.lstrip("/\\"),
                "line": line_num,
                "confidence": "high" if item.get("Verified") else "medium",
            }
        )
    return findings
