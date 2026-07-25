"""
runner — per-tool security scanner runners (package).

Split from the former single-file ``runner.py`` into cohesive submodules:
  * base          — subprocess helpers (`_run`, `_run_json_tool`), SEVERITY_MAP
  * sast          — source analysers (bandit, semgrep, njsscan, eslint, gosec, bearer)
  * deps          — dependency/CVE scanners (pip-audit, npm, trivy, grype, osv, safety)
  * secrets       — secret detectors (gitleaks, trufflehog, detect-secrets)
  * iac           — IaC misconfig scanners (checkov, hadolint, tfsec)
  * orchestrator  — Probe registry, `_count_severities`, `_run_all_tools`

Every name the previous module exposed is re-exported here so that
``from app.services.code_scan.runner import _run, _run_bandit, ...`` and the
existing test patch targets (`...runner._run_bandit`, ...) keep working. The
low-level ``_run`` is patched at ``...runner.base._run`` since tool runners call
it through the ``base`` module.
"""

from __future__ import annotations

from .base import NOT_INSTALLED, SEVERITY_MAP, _run, _run_json_tool
from .deps import (
    _run_grype,
    _run_npm_audit,
    _run_osv_scanner,
    _run_pip_audit,
    _run_safety,
    _run_trivy,
)
from .iac import _run_checkov, _run_hadolint, _run_tfsec
from .orchestrator import PROBES, Probe, _count_severities, _run_all_tools
from .sast import (
    _run_bandit,
    _run_bearer,
    _run_eslint_security,
    _run_gosec,
    _run_njsscan,
    _run_semgrep,
)
from .secrets import _run_detect_secrets, _run_gitleaks, _run_trufflehog

__all__ = [
    # base
    "NOT_INSTALLED",
    "SEVERITY_MAP",
    "_run",
    "_run_json_tool",
    # orchestrator
    "Probe",
    "PROBES",
    "_count_severities",
    "_run_all_tools",
    # sast
    "_run_bandit",
    "_run_semgrep",
    "_run_njsscan",
    "_run_eslint_security",
    "_run_gosec",
    "_run_bearer",
    # deps
    "_run_pip_audit",
    "_run_npm_audit",
    "_run_trivy",
    "_run_grype",
    "_run_osv_scanner",
    "_run_safety",
    # secrets
    "_run_gitleaks",
    "_run_trufflehog",
    "_run_detect_secrets",
    # iac
    "_run_checkov",
    "_run_hadolint",
    "_run_tfsec",
]
