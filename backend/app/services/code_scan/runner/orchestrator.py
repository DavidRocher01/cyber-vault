"""
orchestrator.py — tool registry, severity counters and the run-all driver.

Defines the `Probe` descriptor (one per integrated security tool), the ordered
`PROBES` registry, `_count_severities`, and `_run_all_tools` which walks the
registry, skips absent binaries and aggregates every runner's findings.

Runner functions are resolved by attribute name on the `code_scan.runner`
package *at call time* (not captured at import) so that test patches applied to
the package — e.g. ``patch("...runner._run_bandit")`` — remain effective.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Probe:
    """Descriptor for one security tool wired into the code scan.

    name    — human-readable label used in logs and the unavailable list
    attr    — name of the runner function on the ``code_scan.runner`` package,
              resolved at call time so patches on the package are honoured
    binary  — executable that must be present on PATH for the tool to run
    """

    name: str
    attr: str
    binary: str


# Registre statique : ordre d'execution des outils. Chaque Probe reference sa
# fonction runner par nom d'attribut (resolu sur le package a l'execution) afin
# que les patches de tests (runner._run_bandit, ...) restent effectifs.
PROBES: list[Probe] = [
    Probe("Bandit", "_run_bandit", "bandit"),
    Probe("Semgrep", "_run_semgrep", "semgrep"),
    Probe("pip-audit", "_run_pip_audit", "pip-audit"),
    Probe("gitleaks", "_run_gitleaks", "gitleaks"),
    Probe("trufflehog", "_run_trufflehog", "trufflehog"),
    Probe("detect-secrets", "_run_detect_secrets", "detect-secrets"),
    Probe("npm audit", "_run_npm_audit", "npm"),
    Probe("njsscan", "_run_njsscan", "njsscan"),
    Probe("eslint-security", "_run_eslint_security", "eslint"),
    Probe("trivy", "_run_trivy", "trivy"),
    Probe("grype", "_run_grype", "grype"),
    Probe("osv-scanner", "_run_osv_scanner", "osv-scanner"),
    Probe("safety", "_run_safety", "safety"),
    Probe("checkov", "_run_checkov", "checkov"),
    Probe("hadolint", "_run_hadolint", "hadolint"),
    Probe("tfsec", "_run_tfsec", "tfsec"),
    Probe("gosec", "_run_gosec", "gosec"),
    Probe("bearer", "_run_bearer", "bearer"),
]


# ─── severity counters ────────────────────────────────────────────────────────


def _count_severities(findings: list[dict]) -> dict:
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        sev = f.get("severity", "low")
        if sev in counts:
            counts[sev] += 1
    return counts


# ─── shared tool orchestrator ─────────────────────────────────────────────────


def _run_all_tools(scan_id: int, repo_dir: str) -> tuple[list[dict], dict, list[str]]:
    """Run every security tool on repo_dir.
    Returns (all_findings, severity_counts, unavailable_tools).
    """
    import shutil as _shutil
    import sys

    from loguru import logger

    from app.services.code_scan import runner

    venv_scripts = os.path.dirname(sys.executable)
    current_path = os.environ.get("PATH", "")
    if venv_scripts not in current_path:
        os.environ["PATH"] = venv_scripts + os.pathsep + current_path

    all_findings: list[dict] = []
    unavailable: list[str] = []

    for probe in PROBES:
        if not _shutil.which(probe.binary):
            logger.warning(f"CodeScan {scan_id}: {probe.name} not installed, skipping")
            unavailable.append(probe.name)
            continue
        logger.info(f"CodeScan {scan_id}: running {probe.name}")
        runner_fn = getattr(runner, probe.attr)
        all_findings.extend(runner_fn(repo_dir))

    return all_findings, _count_severities(all_findings), unavailable
