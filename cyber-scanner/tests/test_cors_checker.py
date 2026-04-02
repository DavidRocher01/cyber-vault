"""
Tests for scanner/cors_checker.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.cors_checker import check_cors, _probe, EVIL_ORIGIN

URL = "https://example.com"


# ---------------------------------------------------------------------------
# _probe
# ---------------------------------------------------------------------------

def _make_probe_response(acao: str, acac: str = "", acam: str = "", status_code: int = 200):
    headers = {
        "Access-Control-Allow-Origin": acao,
        "Access-Control-Allow-Credentials": acac,
        "Access-Control-Allow-Methods": acam,
    }
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.headers.get = lambda k, d="": headers.get(k, d)
    return mock_resp


def test_probe_returns_headers_on_success():
    mock_resp = _make_probe_response("*", "true", "GET, POST")
    with patch("scanner.cors_checker.requests.get", return_value=mock_resp):
        result = _probe(URL, EVIL_ORIGIN)
    assert result["acao"] == "*"
    assert result["acac"] == "true"


def test_probe_returns_error_on_connection_failure():
    with patch("scanner.cors_checker.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _probe(URL, EVIL_ORIGIN)
    assert result["status_code"] == "error"


# ---------------------------------------------------------------------------
# check_cors
# ---------------------------------------------------------------------------

def test_check_cors_critical_wildcard_with_credentials():
    def fake_probe(url, origin, timeout=10):
        return {"acao": "*", "acac": "true", "acam": "GET", "status_code": "200"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    assert result["status"] == "CRITICAL"
    assert result["vulnerable"] is True


def test_check_cors_critical_reflected_origin_with_credentials():
    def fake_probe(url, origin, timeout=10):
        if origin == EVIL_ORIGIN:
            return {"acao": EVIL_ORIGIN, "acac": "true", "acam": "GET", "status_code": "200"}
        return {"acao": "", "acac": "", "acam": "", "status_code": "200"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    assert result["status"] == "CRITICAL"
    assert result["vulnerable"] is True


def test_check_cors_warning_wildcard_without_credentials():
    def fake_probe(url, origin, timeout=10):
        return {"acao": "*", "acac": "", "acam": "GET", "status_code": "200"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    assert result["status"] == "WARNING"
    assert result["vulnerable"] is False


def test_check_cors_warning_null_origin_accepted():
    def fake_probe(url, origin, timeout=10):
        if origin == "null":
            return {"acao": "null", "acac": "", "acam": "", "status_code": "200"}
        return {"acao": "", "acac": "", "acam": "", "status_code": "200"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    assert result["status"] == "WARNING"


def test_check_cors_ok_when_no_cors_headers():
    def fake_probe(url, origin, timeout=10):
        return {"acao": "", "acac": "", "acam": "", "status_code": "200"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    assert result["status"] == "OK"
    assert result["issues"] == []


def test_check_cors_critical_on_connection_error():
    def fake_probe(url, origin, timeout=10):
        return {"acao": "", "acac": "", "acam": "", "status_code": "error"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_check_cors_returns_expected_keys():
    def fake_probe(url, origin, timeout=10):
        return {"acao": "", "acac": "", "acam": "", "status_code": "200"}
    with patch("scanner.cors_checker._probe", side_effect=fake_probe):
        result = check_cors(URL)
    for key in ("allow_origin", "allow_credentials", "issues", "vulnerable", "status", "error"):
        assert key in result
