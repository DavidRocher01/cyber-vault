"""
sast.py — static application security testing runners.

Source-code analysers: Bandit (Python), Semgrep (multi-lang), njsscan &
eslint-security (JS/TS), gosec (Go), Bearer (PII/data-security).
Each returns a list of normalised finding dicts.
"""

from __future__ import annotations

import json
import os

from loguru import logger

from . import base


def _run_bandit(repo_dir: str) -> list[dict]:
    """Run Bandit on all Python files. Returns list of findings."""
    data = base._run_json_tool(
        ["bandit", "-r", ".", "-f", "json", "-q", "--exit-zero"],
        repo_dir,
        "bandit",
    )
    if data is None:
        return []

    findings = []
    for issue in data.get("results", []):
        severity = base.SEVERITY_MAP.get(issue.get("issue_severity", "").upper(), "low")
        findings.append(
            {
                "tool": "bandit",
                "severity": severity,
                "rule": issue.get("test_id", ""),
                "title": issue.get("test_name", ""),
                "message": issue.get("issue_text", ""),
                "file": issue.get("filename", "").replace(repo_dir, "").lstrip("/\\"),
                "line": issue.get("line_number"),
                "confidence": issue.get("issue_confidence", ""),
            }
        )
    return findings


def _run_semgrep(repo_dir: str) -> list[dict]:
    """Run Semgrep with the auto ruleset. Returns list of findings."""
    data = base._run_json_tool(
        ["semgrep", "scan", "--config=auto", "--json", "--quiet", "--timeout=60"],
        repo_dir,
        "semgrep",
        timeout=180,
    )
    if data is None:
        return []

    findings = []
    for r in data.get("results", []):
        extra = r.get("extra", {})
        sev_raw = extra.get("severity", extra.get("metadata", {}).get("severity", "INFO")).upper()
        severity = base.SEVERITY_MAP.get(sev_raw, "low")

        findings.append(
            {
                "tool": "semgrep",
                "severity": severity,
                "rule": r.get("check_id", ""),
                "title": r.get("check_id", "").split(".")[-1].replace("-", " ").title(),
                "message": extra.get("message", ""),
                "file": r.get("path", "").replace(repo_dir, "").lstrip("/\\"),
                "line": r.get("start", {}).get("line"),
                "confidence": "",
            }
        )
    return findings


def _run_njsscan(repo_dir: str) -> list[dict]:
    """Run njsscan for Node.js / JavaScript SAST."""
    data = base._run_json_tool(
        ["njsscan", "--json", "-o", "-", "."],
        repo_dir,
        "njsscan",
        timeout=120,
    )
    if data is None:
        return []

    severity_map = {"ERROR": "high", "WARNING": "medium", "INFO": "low"}
    findings = []
    for section in ("nodejs", "templates"):
        for rule_id, rule_data in (data.get(section) or {}).items():
            if not isinstance(rule_data, dict):
                continue
            sev = severity_map.get(
                rule_data.get("metadata", {}).get("severity", "WARNING").upper(),
                "medium",
            )
            for match in rule_data.get("files", []):
                findings.append(
                    {
                        "tool": "njsscan",
                        "severity": sev,
                        "rule": rule_id,
                        "title": rule_data.get("metadata", {}).get("description", rule_id),
                        "message": rule_data.get("metadata", {}).get("description", ""),
                        "file": match.get("file_path", "").lstrip("/\\"),
                        "line": (match.get("match_lines") or [None])[0],
                        "confidence": "",
                    }
                )
    return findings


def _run_eslint_security(repo_dir: str) -> list[dict]:
    """Run eslint with eslint-plugin-security on JS/TS files."""
    import glob as _glob

    js_files = [
        f
        for ext in ("*.js", "*.ts", "*.jsx", "*.tsx")
        for f in _glob.glob(os.path.join(repo_dir, "**", ext), recursive=True)
        if "node_modules" not in f
    ]
    if not js_files:
        logger.info("eslint-security: no JS/TS files found, skipping")
        return []

    eslint_config = os.path.join(repo_dir, ".eslintrc-cyberscan.json")
    with open(eslint_config, "w") as f:
        json.dump(
            {
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
            },
            f,
        )

    code, stdout, _ = base._run(
        [
            "eslint",
            "--config",
            eslint_config,
            "--format",
            "json",
            "--no-eslintrc",
            "--ext",
            ".js,.ts,.jsx,.tsx",
            ".",
        ],
        cwd=repo_dir,
        timeout=120,
    )
    try:
        os.unlink(eslint_config)
    except OSError as exc:
        logger.debug("Nettoyage config eslint temporaire echoue : {}", exc)

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
            findings.append(
                {
                    "tool": "eslint-security",
                    "severity": sev,
                    "rule": rule,
                    "title": rule.replace("security/", "").replace("-", " ").title()
                    if rule
                    else "ESLint security",
                    "message": msg.get("message", ""),
                    "file": rel_path,
                    "line": msg.get("line"),
                    "confidence": "",
                }
            )
    return findings


def _run_gosec(repo_dir: str) -> list[dict]:
    """Run gosec for Go source security analysis."""
    import glob as _glob

    if not _glob.glob(os.path.join(repo_dir, "**/*.go"), recursive=True):
        logger.info("gosec: no .go files found, skipping")
        return []
    data = base._run_json_tool(
        ["gosec", "-fmt", "json", "-stdout", "-quiet", "./..."],
        repo_dir,
        "gosec",
        timeout=180,
    )
    if data is None:
        return []

    severity_map = {"HIGH": "high", "MEDIUM": "medium", "LOW": "low"}
    findings = []
    for issue in data.get("Issues", []) or []:
        sev = severity_map.get(issue.get("severity", "LOW").upper(), "low")
        findings.append(
            {
                "tool": "gosec",
                "severity": sev,
                "rule": issue.get("rule_id", ""),
                "title": issue.get("details", issue.get("rule_id", "")),
                "message": f"{issue.get('details', '')} (confidence: {issue.get('confidence', '')})",
                "file": (issue.get("file") or "").replace(repo_dir, "").lstrip("/\\"),
                "line": issue.get("line"),
                "confidence": issue.get("confidence", ""),
            }
        )
    return findings


def _run_bearer(repo_dir: str) -> list[dict]:
    """Run Bearer to detect PII leaks and data-security issues."""
    code, stdout, stderr = base._run(
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

    severity_map = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "warning": "medium",
    }
    findings = []
    for sev_key, items in data.items():
        if not isinstance(items, list):
            continue
        sev = severity_map.get(sev_key.lower(), "medium")
        for item in items:
            findings.append(
                {
                    "tool": "bearer",
                    "severity": sev,
                    "rule": item.get("rule_id", ""),
                    "title": item.get("title", item.get("rule_id", "Bearer finding")),
                    "message": item.get("description", item.get("detail", ""))[:300],
                    "file": (item.get("filename") or "").lstrip("/\\"),
                    "line": item.get("line_number"),
                    "confidence": "high",
                }
            )
    return findings
