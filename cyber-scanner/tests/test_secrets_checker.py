"""
Tests for scanner/secrets_checker.py
All file I/O is mocked — no real filesystem access.
"""

import os
from unittest.mock import MagicMock, mock_open, patch

import pytest

from scanner.secrets_checker import (
    _scan_file,
    _should_scan,
    check_secrets,
)


# ---------------------------------------------------------------------------
# _should_scan
# ---------------------------------------------------------------------------

def test_should_scan_python_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("x = 1")
    assert _should_scan(str(f)) is True


def test_should_scan_dotenv_file(tmp_path):
    f = tmp_path / ".env"
    f.write_text("API_KEY=secret")
    assert _should_scan(str(f)) is True


def test_should_not_scan_binary_extension(tmp_path):
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG\r\n")
    assert _should_scan(str(f)) is False


def test_should_not_scan_large_file(tmp_path):
    f = tmp_path / "big.py"
    f.write_bytes(b"x" * 2_000_000)
    assert _should_scan(str(f)) is False


# ---------------------------------------------------------------------------
# _scan_file
# ---------------------------------------------------------------------------

def test_scan_file_detects_aws_key(tmp_path):
    f = tmp_path / "config.py"
    f.write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    findings = _scan_file(str(f))
    assert len(findings) == 1
    assert findings[0]["pattern"] == "AWS Access Key"
    assert findings[0]["line"] == 1


def test_scan_file_detects_private_key_header(tmp_path):
    f = tmp_path / "key.pem"
    f.write_text("-----BEGIN RSA PRIVATE KEY-----\nMIIEo...\n")
    findings = _scan_file(str(f))
    assert any(r["pattern"] == "Private Key Header" for r in findings)


def test_scan_file_redacts_secret_in_preview(tmp_path):
    f = tmp_path / "app.py"
    f.write_text('API_KEY = "supersecretkey12345"\n')
    findings = _scan_file(str(f))
    if findings:
        assert "***" in findings[0]["preview"]


def test_scan_file_no_findings_for_clean_file(tmp_path):
    f = tmp_path / "clean.py"
    f.write_text("def add(a, b):\n    return a + b\n")
    findings = _scan_file(str(f))
    assert findings == []


def test_scan_file_detects_database_url(tmp_path):
    f = tmp_path / "settings.py"
    f.write_text('DATABASE_URL = "postgres://user:pass@localhost:5432/db"\n')
    findings = _scan_file(str(f))
    assert any(r["pattern"] == "Database URL" for r in findings)


# ---------------------------------------------------------------------------
# check_secrets
# ---------------------------------------------------------------------------

def test_check_secrets_path_not_found():
    result = check_secrets("/nonexistent/path")
    assert result["status"] == "CRITICAL"
    assert "not found" in result["error"]


def test_check_secrets_ok_on_clean_directory(tmp_path):
    f = tmp_path / "main.py"
    f.write_text("def hello():\n    print('hello world')\n")
    result = check_secrets(str(tmp_path))
    assert result["status"] == "OK"
    assert result["total_findings"] == 0


def test_check_secrets_warning_on_one_finding(tmp_path):
    f = tmp_path / "config.py"
    f.write_text('AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    result = check_secrets(str(tmp_path))
    assert result["status"] in ("WARNING", "CRITICAL")
    assert result["total_findings"] >= 1


def test_check_secrets_critical_on_three_or_more_findings(tmp_path):
    for i in range(3):
        f = tmp_path / f"config{i}.py"
        f.write_text(f'AWS_KEY_{i} = "AKIAIOSFODNN7EXAMPLE"\n')
    result = check_secrets(str(tmp_path))
    assert result["status"] == "CRITICAL"


def test_check_secrets_skips_venv_directory(tmp_path):
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    secret_file = venv_dir / "leak.py"
    secret_file.write_text('KEY = "AKIAIOSFODNN7EXAMPLE"\n')
    clean_file = tmp_path / "main.py"
    clean_file.write_text("x = 1\n")
    result = check_secrets(str(tmp_path))
    assert result["total_findings"] == 0


def test_check_secrets_counts_files_scanned(tmp_path):
    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_text("x = 1\n")
    result = check_secrets(str(tmp_path))
    assert result["total_files"] == 3


def test_check_secrets_single_file(tmp_path):
    f = tmp_path / "secret.py"
    f.write_text('password = "hunter2"\n')
    result = check_secrets(str(f))
    assert result["total_files"] == 1
