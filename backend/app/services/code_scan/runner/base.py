"""
base.py — low-level subprocess helpers and shared severity table.

Provides the primitives shared by every per-tool runner:
  * `_run`            — run a subprocess, tolerating missing binaries/timeouts
  * `_run_json_tool`  — run a JSON-emitting tool and parse its stdout
  * `SEVERITY_MAP`    — normalise scanner severity labels to internal levels
  * `NOT_INSTALLED`   — sentinel return code for an absent binary

Tool runners call these via the module (``base._run(...)``) so a single patch
target (`...runner.base._run`) intercepts subprocess execution in tests.
"""

from __future__ import annotations

import json
import subprocess

from loguru import logger

# ─── constants ────────────────────────────────────────────────────────────────

NOT_INSTALLED = -2  # sentinel returncode meaning the binary was not found on PATH


# ─── low-level subprocess helper ─────────────────────────────────────────────


def _run(cmd: list[str], cwd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout, stderr).
    Returns (NOT_INSTALLED, "", ...) when the binary is absent from PATH.
    """
    try:
        proc = subprocess.run(  # nosec B603 — cmd is always a hardcoded list, never a shell string
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
        return NOT_INSTALLED, "", f"Command not found: {cmd[0]}"


def _run_json_tool(cmd: list[str], cwd: str, tool: str, timeout: int = 120):
    """Execute un outil qui emet du JSON sur stdout et renvoie l'objet parse.

    Factorise le tryptique repete par la plupart des runners : lancement du
    process, garde 'pas de sortie', puis json.loads/except. Renvoie None (et
    logue) si l'outil n'a rien produit ou si le JSON est illisible ; le runner
    appelant se contente alors de `return []`.
    """
    _code, stdout, stderr = _run(cmd, cwd=cwd, timeout=timeout)
    if not stdout:
        logger.warning(f"{tool} produced no output: {stderr[:300]}")
        return None
    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        logger.warning(f"{tool} JSON parse error: {stdout[:200]}")
        return None


# Normalisation des severites : cle en MAJUSCULE (telle qu'emise par les outils)
# -> severite interne. Regroupe les alias des differents scanners (bandit,
# semgrep, trivy, gosec...) en une seule table.
SEVERITY_MAP: dict[str, str] = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "ERROR": "high",
    "MEDIUM": "medium",
    "MODERATE": "medium",
    "WARNING": "medium",
    "LOW": "low",
    "INFO": "low",
    "UNKNOWN": "low",
}
