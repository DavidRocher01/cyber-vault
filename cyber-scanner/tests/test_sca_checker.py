"""
Tests for scanner/sca_checker.py
All tests are fully mocked — no real network calls, no real file I/O.
"""

import json
import textwrap
from io import StringIO
from unittest.mock import MagicMock, mock_open, patch

import pytest

from scanner.sca_checker import (
    _extract_severity,
    _parse_package_json,
    _parse_requirements_txt,
    _query_osv,
    check_sca,
)


# ---------------------------------------------------------------------------
# _parse_requirements_txt
# ---------------------------------------------------------------------------

def test_parse_requirements_txt_with_version():
    content = "requests>=2.31.0\nurllib3==2.0.0\n"
    with patch("builtins.open", mock_open(read_data=content)):
        pkgs = _parse_requirements_txt("requirements.txt")
    assert {"name": "requests", "version": "2.31.0"} in pkgs
    assert {"name": "urllib3", "version": "2.0.0"} in pkgs


def test_parse_requirements_txt_no_version():
    content = "requests\n"
    with patch("builtins.open", mock_open(read_data=content)):
        pkgs = _parse_requirements_txt("requirements.txt")
    assert pkgs[0]["name"] == "requests"
    assert pkgs[0]["version"] is None


def test_parse_requirements_txt_skips_comments_and_flags():
    content = "# comment\n-r other.txt\nflask>=2.0\n"
    with patch("builtins.open", mock_open(read_data=content)):
        pkgs = _parse_requirements_txt("requirements.txt")
    assert len(pkgs) == 1
    assert pkgs[0]["name"] == "flask"


# ---------------------------------------------------------------------------
# _parse_package_json
# ---------------------------------------------------------------------------

def test_parse_package_json_dependencies():
    data = json.dumps({
        "dependencies": {"express": "^4.18.2"},
        "devDependencies": {"jest": "~29.0.0"},
    })
    with patch("builtins.open", mock_open(read_data=data)):
        pkgs = _parse_package_json("package.json")
    names = [p["name"] for p in pkgs]
    assert "express" in names
    assert "jest" in names


def test_parse_package_json_strips_range_prefix():
    data = json.dumps({"dependencies": {"lodash": "^4.17.21"}})
    with patch("builtins.open", mock_open(read_data=data)):
        pkgs = _parse_package_json("package.json")
    assert pkgs[0]["version"] == "4.17.21"


def test_parse_package_json_empty():
    data = json.dumps({})
    with patch("builtins.open", mock_open(read_data=data)):
        pkgs = _parse_package_json("package.json")
    assert pkgs == []


# ---------------------------------------------------------------------------
# _extract_severity
# ---------------------------------------------------------------------------

def test_extract_severity_from_database_specific():
    vuln = {"database_specific": {"severity": "HIGH"}}
    assert _extract_severity(vuln) == "HIGH"


def test_extract_severity_from_ecosystem_specific():
    vuln = {"ecosystem_specific": {"severity": "medium"}}
    assert _extract_severity(vuln) == "MEDIUM"


def test_extract_severity_unknown_fallback():
    vuln = {}
    assert _extract_severity(vuln) == "UNKNOWN"


# ---------------------------------------------------------------------------
# _query_osv
# ---------------------------------------------------------------------------

def test_query_osv_returns_vulns_on_success():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"vulns": [{"id": "GHSA-xxxx"}]}
    mock_resp.raise_for_status = MagicMock()
    with patch("scanner.sca_checker.requests.post", return_value=mock_resp):
        result = _query_osv("requests", "2.25.0", "PyPI")
    assert len(result) == 1
    assert result[0]["id"] == "GHSA-xxxx"


def test_query_osv_returns_empty_on_network_error():
    import requests as req_lib
    with patch("scanner.sca_checker.requests.post", side_effect=req_lib.exceptions.ConnectionError):
        result = _query_osv("requests", "2.25.0", "PyPI")
    assert result == []


def test_query_osv_returns_empty_when_no_vulns_key():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {}
    mock_resp.raise_for_status = MagicMock()
    with patch("scanner.sca_checker.requests.post", return_value=mock_resp):
        result = _query_osv("safe-package", "1.0.0", "PyPI")
    assert result == []


# ---------------------------------------------------------------------------
# check_sca — integration-level (fully mocked)
# ---------------------------------------------------------------------------

def test_check_sca_no_file_provided():
    result = check_sca()
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_check_sca_missing_requirements_file():
    with patch("scanner.sca_checker.os.path.exists", return_value=False):
        result = check_sca(requirements_path="missing.txt")
    assert result["status"] == "CRITICAL"
    assert "not found" in result["error"]


def test_check_sca_ok_no_vulns():
    content = "requests>=2.31.0\n"
    with patch("scanner.sca_checker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)), \
         patch("scanner.sca_checker._query_osv", return_value=[]):
        result = check_sca(requirements_path="requirements.txt")
    assert result["status"] == "OK"
    assert result["total_vulns"] == 0


def test_check_sca_critical_when_high_severity_vuln():
    content = "requests>=2.25.0\n"
    fake_vuln = {
        "id": "GHSA-xxxx",
        "aliases": ["CVE-2022-0001"],
        "summary": "Remote code execution",
        "database_specific": {"severity": "HIGH"},
    }
    with patch("scanner.sca_checker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)), \
         patch("scanner.sca_checker._query_osv", return_value=[fake_vuln]):
        result = check_sca(requirements_path="requirements.txt")
    assert result["status"] == "CRITICAL"
    assert result["total_vulns"] == 1
    assert result["vulns"][0]["cve_ids"] == ["CVE-2022-0001"]


def test_check_sca_warning_when_medium_severity_vuln():
    content = "flask>=2.0\n"
    fake_vuln = {
        "id": "GHSA-yyyy",
        "aliases": [],
        "summary": "Information disclosure",
        "database_specific": {"severity": "MEDIUM"},
    }
    with patch("scanner.sca_checker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)), \
         patch("scanner.sca_checker._query_osv", return_value=[fake_vuln]):
        result = check_sca(requirements_path="requirements.txt")
    assert result["status"] == "WARNING"
    assert result["vulns"][0]["cve_ids"] == ["GHSA-yyyy"]  # fallback to OSV id


def test_check_sca_counts_packages_correctly():
    content = "requests>=2.31.0\nurllib3==2.0.0\nflask>=2.0\n"
    with patch("scanner.sca_checker.os.path.exists", return_value=True), \
         patch("builtins.open", mock_open(read_data=content)), \
         patch("scanner.sca_checker._query_osv", return_value=[]):
        result = check_sca(requirements_path="requirements.txt")
    assert result["total_packages"] == 3
