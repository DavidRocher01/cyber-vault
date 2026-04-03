"""
Tests for scanner/open_redirect.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.open_redirect import (
    _is_redirect_response,
    _probe_redirect,
    check_open_redirect,
)

URL = "https://example.com"


# ---------------------------------------------------------------------------
# _probe_redirect
# ---------------------------------------------------------------------------

def test_probe_redirect_detects_vulnerable_redirect():
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.headers = {"Location": "https://evil-attacker.com"}
    with patch("scanner.open_redirect.requests.get", return_value=mock_resp):
        result = _probe_redirect(URL, "redirect", "https://evil-attacker.com")
    assert result["vulnerable"] is True
    assert result["status_code"] == 302


def test_probe_redirect_not_vulnerable_on_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {}
    with patch("scanner.open_redirect.requests.get", return_value=mock_resp):
        result = _probe_redirect(URL, "redirect", "https://evil-attacker.com")
    assert result["vulnerable"] is False


def test_probe_redirect_not_vulnerable_when_location_is_safe():
    mock_resp = MagicMock()
    mock_resp.status_code = 302
    mock_resp.headers = {"Location": "https://example.com/dashboard"}
    with patch("scanner.open_redirect.requests.get", return_value=mock_resp):
        result = _probe_redirect(URL, "next", "https://evil-attacker.com")
    assert result["vulnerable"] is False


def test_probe_redirect_returns_on_connection_error():
    with patch("scanner.open_redirect.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _probe_redirect(URL, "url", "https://evil-attacker.com")
    assert result["vulnerable"] is False
    assert result["status_code"] is None


# ---------------------------------------------------------------------------
# _is_redirect_response
# ---------------------------------------------------------------------------

def test_is_redirect_response_true_when_vulnerable():
    probe = {"vulnerable": True, "status_code": 302, "location": "https://evil-attacker.com"}
    assert _is_redirect_response(probe) is True


def test_is_redirect_response_false_when_not_vulnerable():
    probe = {"vulnerable": False, "status_code": 200, "location": ""}
    assert _is_redirect_response(probe) is False


# ---------------------------------------------------------------------------
# check_open_redirect
# ---------------------------------------------------------------------------

def test_check_open_redirect_returns_expected_keys():
    safe = {"param": "redirect", "payload": "x", "status_code": 200, "location": "", "vulnerable": False}
    with patch("scanner.open_redirect._probe_redirect", return_value=safe):
        result = check_open_redirect(URL)
    for key in ("vulnerable", "findings", "tested", "status", "error"):
        assert key in result


def test_check_open_redirect_critical_on_finding():
    vuln = {"param": "redirect", "payload": "https://evil-attacker.com", "status_code": 302,
            "location": "https://evil-attacker.com", "vulnerable": True}
    with patch("scanner.open_redirect._probe_redirect", return_value=vuln):
        result = check_open_redirect(URL)
    assert result["status"] == "CRITICAL"
    assert result["vulnerable"] is True
    assert len(result["findings"]) > 0


def test_check_open_redirect_ok_when_all_safe():
    safe = {"param": "redirect", "payload": "x", "status_code": 200, "location": "", "vulnerable": False}
    with patch("scanner.open_redirect._probe_redirect", return_value=safe):
        result = check_open_redirect(URL)
    assert result["status"] == "OK"
    assert result["vulnerable"] is False


def test_check_open_redirect_tested_count_positive():
    safe = {"param": "x", "payload": "y", "status_code": 200, "location": "", "vulnerable": False}
    with patch("scanner.open_redirect._probe_redirect", return_value=safe):
        result = check_open_redirect(URL)
    assert result["tested"] > 0
