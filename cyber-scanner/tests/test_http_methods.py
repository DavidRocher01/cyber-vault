"""
Tests for scanner/http_methods.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.http_methods import (
    _parse_options,
    _probe_method,
    check_http_methods,
)

URL = "https://example.com"


# ---------------------------------------------------------------------------
# _probe_method
# ---------------------------------------------------------------------------

def test_probe_method_returns_allowed_on_200():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch("scanner.http_methods.requests.request", return_value=mock_resp):
        result = _probe_method(URL, "PUT")
    assert result["allowed"] is True
    assert result["status_code"] == 200
    assert result["method"] == "PUT"


def test_probe_method_returns_not_allowed_on_405():
    mock_resp = MagicMock()
    mock_resp.status_code = 405
    with patch("scanner.http_methods.requests.request", return_value=mock_resp):
        result = _probe_method(URL, "DELETE")
    assert result["allowed"] is False


def test_probe_method_returns_not_allowed_on_501():
    mock_resp = MagicMock()
    mock_resp.status_code = 501
    with patch("scanner.http_methods.requests.request", return_value=mock_resp):
        result = _probe_method(URL, "TRACE")
    assert result["allowed"] is False


def test_probe_method_returns_error_on_connection_error():
    with patch("scanner.http_methods.requests.request", side_effect=req_lib.exceptions.ConnectionError("timeout")):
        result = _probe_method(URL, "GET")
    assert result["allowed"] is False
    assert result["error"] is not None


# ---------------------------------------------------------------------------
# _parse_options
# ---------------------------------------------------------------------------

def test_parse_options_returns_methods_from_allow_header():
    mock_resp = MagicMock()
    mock_resp.headers = {"Allow": "GET, POST, OPTIONS, HEAD"}
    with patch("scanner.http_methods.requests.options", return_value=mock_resp):
        result = _parse_options(URL)
    assert "GET" in result
    assert "POST" in result
    assert "OPTIONS" in result


def test_parse_options_returns_empty_on_error():
    with patch("scanner.http_methods.requests.options", side_effect=req_lib.exceptions.ConnectionError):
        result = _parse_options(URL)
    assert result == []


# ---------------------------------------------------------------------------
# check_http_methods
# ---------------------------------------------------------------------------

def test_check_http_methods_returns_expected_keys():
    safe_probe = {"method": "OPTIONS", "status_code": 200, "allowed": False, "error": None}
    with patch("scanner.http_methods._parse_options", return_value=["GET", "POST"]), \
         patch("scanner.http_methods._probe_method", return_value=safe_probe):
        result = check_http_methods(URL)
    for key in ("allowed_methods", "dangerous_allowed", "options_declared", "probes", "status", "error"):
        assert key in result


def test_check_http_methods_critical_on_trace():
    def fake_probe(url, method):
        return {"method": method, "status_code": 200 if method == "TRACE" else 405, "allowed": method == "TRACE", "error": None}
    with patch("scanner.http_methods._parse_options", return_value=[]), \
         patch("scanner.http_methods._probe_method", side_effect=fake_probe):
        result = check_http_methods(URL)
    assert result["status"] == "CRITICAL"
    assert "TRACE" in result["dangerous_allowed"]


def test_check_http_methods_critical_on_put():
    def fake_probe(url, method):
        return {"method": method, "status_code": 200 if method == "PUT" else 405, "allowed": method == "PUT", "error": None}
    with patch("scanner.http_methods._parse_options", return_value=[]), \
         patch("scanner.http_methods._probe_method", side_effect=fake_probe):
        result = check_http_methods(URL)
    assert result["status"] == "CRITICAL"
    assert "PUT" in result["dangerous_allowed"]


def test_check_http_methods_ok_when_all_blocked():
    safe_probe = {"method": "GET", "status_code": 405, "allowed": False, "error": None}
    with patch("scanner.http_methods._parse_options", return_value=["GET", "POST"]), \
         patch("scanner.http_methods._probe_method", return_value=safe_probe):
        result = check_http_methods(URL)
    assert result["status"] == "OK"
    assert result["dangerous_allowed"] == []


def test_check_http_methods_warning_on_connect():
    def fake_probe(url, method):
        return {"method": method, "status_code": 200 if method == "CONNECT" else 405, "allowed": method == "CONNECT", "error": None}
    with patch("scanner.http_methods._parse_options", return_value=[]), \
         patch("scanner.http_methods._probe_method", side_effect=fake_probe):
        result = check_http_methods(URL)
    assert result["status"] == "WARNING"
