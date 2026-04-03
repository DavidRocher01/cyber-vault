"""
Tests for scanner/directory_listing.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.directory_listing import (
    _probe_path,
    _severity_rank,
    check_directory_listing,
)

URL = "https://example.com"


# ---------------------------------------------------------------------------
# _severity_rank
# ---------------------------------------------------------------------------

def test_severity_rank_critical_is_lowest():
    assert _severity_rank("CRITICAL") < _severity_rank("WARNING")


def test_severity_rank_unknown_returns_2():
    assert _severity_rank("UNKNOWN") == 2


# ---------------------------------------------------------------------------
# _probe_path
# ---------------------------------------------------------------------------

def test_probe_path_returns_finding_on_200_with_pattern():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "[core]\n\trepositoryformatversion = 0"
    with patch("scanner.directory_listing.requests.get", return_value=mock_resp):
        path_def = {"path": "/.git/config", "category": "source_code", "severity": "CRITICAL", "pattern": r"\[core\]"}
        result = _probe_path(URL, path_def)
    assert result is not None
    assert result["severity"] == "CRITICAL"
    assert result["path"] == "/.git/config"


def test_probe_path_returns_none_when_pattern_not_found():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<html>Normal page</html>"
    with patch("scanner.directory_listing.requests.get", return_value=mock_resp):
        path_def = {"path": "/.env", "category": "secrets", "severity": "CRITICAL", "pattern": r"DB_PASSWORD"}
        result = _probe_path(URL, path_def)
    assert result is None


def test_probe_path_returns_none_on_404():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"
    with patch("scanner.directory_listing.requests.get", return_value=mock_resp):
        path_def = {"path": "/admin/", "category": "admin", "severity": "WARNING", "pattern": None}
        result = _probe_path(URL, path_def)
    assert result is None


def test_probe_path_detects_directory_listing():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<title>Index of /uploads/</title>"
    with patch("scanner.directory_listing.requests.get", return_value=mock_resp):
        path_def = {"path": "/uploads/", "category": "listing", "severity": "WARNING", "pattern": r"Index of"}
        result = _probe_path(URL, path_def)
    assert result is not None
    assert result["is_listing"] is True


def test_probe_path_returns_none_on_connection_error():
    with patch("scanner.directory_listing.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        path_def = {"path": "/.env", "category": "secrets", "severity": "CRITICAL", "pattern": r"DB_"}
        result = _probe_path(URL, path_def)
    assert result is None


# ---------------------------------------------------------------------------
# check_directory_listing
# ---------------------------------------------------------------------------

def test_check_directory_listing_returns_expected_keys():
    with patch("scanner.directory_listing._probe_path", return_value=None):
        result = check_directory_listing(URL)
    for key in ("findings", "total_critical", "total_warning", "status", "error"):
        assert key in result


def test_check_directory_listing_critical_on_finding():
    finding = {"path": "/.git/config", "url": URL + "/.git/config", "category": "source_code",
               "severity": "CRITICAL", "status_code": 200, "is_listing": False}
    with patch("scanner.directory_listing._probe_path", return_value=finding):
        result = check_directory_listing(URL)
    assert result["status"] == "CRITICAL"
    assert result["total_critical"] > 0


def test_check_directory_listing_warning_on_warning_finding():
    def fake_probe(url, path_def):
        if path_def["severity"] == "WARNING":
            return {"path": path_def["path"], "url": url, "category": path_def["category"],
                    "severity": "WARNING", "status_code": 200, "is_listing": False}
        return None
    with patch("scanner.directory_listing._probe_path", side_effect=fake_probe):
        result = check_directory_listing(URL)
    assert result["status"] in ("WARNING", "CRITICAL")


def test_check_directory_listing_ok_when_all_safe():
    with patch("scanner.directory_listing._probe_path", return_value=None):
        result = check_directory_listing(URL)
    assert result["status"] == "OK"
    assert result["findings"] == []
