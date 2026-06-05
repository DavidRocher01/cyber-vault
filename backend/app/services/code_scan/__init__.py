"""
services/code_scan — Code security analysis sub-package.

Re-exports the full public (and internal) API so that existing imports such as
    from app.services.code_scan_service import run_code_scan, _run_bandit, ...
continue to work after the monolith was replaced by code_scan_service.py shim.
"""

# Public entry-points
# Runner internals (imported by tests)
from .runner import (
    NOT_INSTALLED,
    _count_severities,
    _run,
    _run_all_tools,
    _run_bandit,
    _run_bearer,
    _run_checkov,
    _run_detect_secrets,
    _run_eslint_security,
    _run_gitleaks,
    _run_gosec,
    _run_grype,
    _run_hadolint,
    _run_njsscan,
    _run_npm_audit,
    _run_osv_scanner,
    _run_pip_audit,
    _run_safety,
    _run_semgrep,
    _run_tfsec,
    _run_trivy,
    _run_trufflehog,
)
from .tasks import run_code_scan, run_code_scan_zip

# URL helpers
from .utils import _extract_repo_name, _redact_url, _sanitize_repo_url

__all__ = [
    # public
    "run_code_scan",
    "run_code_scan_zip",
    # utils
    "_sanitize_repo_url",
    "_redact_url",
    "_extract_repo_name",
    # runner
    "NOT_INSTALLED",
    "_run",
    "_run_all_tools",
    "_count_severities",
    "_run_bandit",
    "_run_semgrep",
    "_run_gitleaks",
    "_run_npm_audit",
    "_run_detect_secrets",
    "_run_trivy",
    "_run_checkov",
    "_run_pip_audit",
    "_run_trufflehog",
    "_run_njsscan",
    "_run_bearer",
    "_run_gosec",
    "_run_eslint_security",
    "_run_osv_scanner",
    "_run_safety",
    "_run_hadolint",
    "_run_tfsec",
    "_run_grype",
]
