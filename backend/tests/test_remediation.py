"""
Unit tests — scanner.remediation
Covers: generate_remediation returns expected script keys,
        UFW includes deny rules for critical ports,
        FastAPI middleware includes missing headers.
"""

import os
import sys
import tempfile
import pytest

from pathlib import Path

# Add cyber-scanner to path (mirrors scan_service.py setup)
SCANNER_DIR = Path(__file__).resolve().parents[3] / "cyber-scanner"
if str(SCANNER_DIR) not in sys.path:
    sys.path.insert(0, str(SCANNER_DIR))

from scanner.remediation import generate_remediation


# ── tests ─────────────────────────────────────────────────────────────────────

def test_generate_remediation_always_produces_ufw_and_ssh():
    """UFW and SSH scripts are always generated regardless of inputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_remediation(
            target_url="https://example.com",
            output_dir=tmpdir,
        )
        assert "ufw" in result
        assert "ssh" in result
        assert os.path.isfile(result["ufw"])
        assert os.path.isfile(result["ssh"])


def test_generate_remediation_fastapi_when_headers_missing():
    """FastAPI middleware is generated when security headers are missing."""
    headers_result = {
        "status": "WARNING",
        "headers_missing": ["Content-Security-Policy", "X-Frame-Options"],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_remediation(
            target_url="https://example.com",
            headers_result=headers_result,
            output_dir=tmpdir,
        )
        assert "fastapi" in result
        with open(result["fastapi"], encoding="utf-8") as f:
            content = f.read()
        assert "Content-Security-Policy" in content


def test_generate_remediation_ufw_includes_deny_for_critical_ports():
    """UFW script contains deny rules for each critical port found."""
    port_result = {
        "status": "WARNING",
        "open_ports": [5432],
        "critical_ports": [5432],
        "error": None,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_remediation(
            target_url="https://example.com",
            port_result=port_result,
            output_dir=tmpdir,
        )
        with open(result["ufw"], encoding="utf-8") as f:
            content = f.read()
        assert "5432" in content
        assert "ufw deny" in content


def test_generate_remediation_scripts_are_valid_files():
    """Generated paths point to existing non-empty files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        result = generate_remediation(
            target_url="https://example.com",
            output_dir=tmpdir,
        )
        for key, path in result.items():
            assert os.path.isfile(path), f"{key} script file not found: {path}"
            assert os.path.getsize(path) > 0, f"{key} script file is empty"
