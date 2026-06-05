"""
code_scan_service.py — compatibility shim.

The implementation has been moved to the services/code_scan/ sub-package.
This module re-exports everything so that existing imports continue to work:

    from app.services.code_scan_service import run_code_scan, _run_bandit, ...
"""

from app.services.code_scan import (  # noqa: F401  (re-export)
    NOT_INSTALLED,
    _count_severities,
    _extract_repo_name,
    _redact_url,
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
    _sanitize_repo_url,
    run_code_scan,
    run_code_scan_zip,
)
