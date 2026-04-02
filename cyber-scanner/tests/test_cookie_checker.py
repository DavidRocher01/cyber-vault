"""
Tests for scanner/cookie_checker.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.cookie_checker import (
    _parse_set_cookie,
    _is_sensitive,
    check_cookies,
)

URL = "https://example.com"


# ---------------------------------------------------------------------------
# _parse_set_cookie
# ---------------------------------------------------------------------------

def test_parse_set_cookie_all_flags_present():
    header = "session=abc123; HttpOnly; Secure; SameSite=Strict"
    result = _parse_set_cookie(header)
    assert result["name"] == "session"
    assert result["http_only"] is True
    assert result["secure"] is True
    assert result["same_site"] == "strict"


def test_parse_set_cookie_no_flags():
    header = "token=xyz789"
    result = _parse_set_cookie(header)
    assert result["name"] == "token"
    assert result["http_only"] is False
    assert result["secure"] is False
    assert result["same_site"] == "none"


def test_parse_set_cookie_samesite_lax():
    header = "csrf=abc; SameSite=Lax"
    result = _parse_set_cookie(header)
    assert result["same_site"] == "lax"


def test_parse_set_cookie_redacts_value():
    header = "session=supersecretvalue"
    result = _parse_set_cookie(header)
    assert "***" in result["value_preview"]
    assert "supersecretvalue" not in result["value_preview"]


# ---------------------------------------------------------------------------
# _is_sensitive
# ---------------------------------------------------------------------------

def test_is_sensitive_session_cookie():
    assert _is_sensitive("session_id") is True


def test_is_sensitive_jwt_cookie():
    assert _is_sensitive("jwt_token") is True


def test_is_sensitive_non_sensitive_cookie():
    assert _is_sensitive("theme_preference") is False


# ---------------------------------------------------------------------------
# check_cookies
# ---------------------------------------------------------------------------

def _make_mock_response(set_cookie_headers: list[str], status_code: int = 200):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.cookies = []
    raw_headers = []
    for v in set_cookie_headers:
        raw_headers.append(("set-cookie", v))
    mock_response.raw.headers.items.return_value = raw_headers
    return mock_response


def test_check_cookies_ok_when_all_flags_present():
    mock_resp = _make_mock_response(["session=abc; HttpOnly; Secure; SameSite=Strict"])
    with patch("scanner.cookie_checker.requests.get", return_value=mock_resp):
        result = check_cookies(URL)
    assert result["status"] == "OK"
    assert result["total_issues"] == 0


def test_check_cookies_warning_when_httponly_missing():
    mock_resp = _make_mock_response(["session=abc; Secure; SameSite=Strict"])
    with patch("scanner.cookie_checker.requests.get", return_value=mock_resp):
        result = check_cookies(URL)
    assert result["status"] in ("WARNING", "CRITICAL")
    assert any("HttpOnly" in i["issue"] for i in result["issues"])


def test_check_cookies_warning_when_secure_missing():
    mock_resp = _make_mock_response(["session=abc; HttpOnly; SameSite=Strict"])
    with patch("scanner.cookie_checker.requests.get", return_value=mock_resp):
        result = check_cookies(URL)
    assert any("Secure" in i["issue"] for i in result["issues"])


def test_check_cookies_critical_when_many_issues():
    # 3 cookies each missing HttpOnly → >= 3 issues → CRITICAL
    mock_resp = _make_mock_response([
        "a=1; Secure; SameSite=Strict",
        "b=2; Secure; SameSite=Strict",
        "c=3; Secure; SameSite=Strict",
    ])
    with patch("scanner.cookie_checker.requests.get", return_value=mock_resp):
        result = check_cookies(URL)
    assert result["status"] == "CRITICAL"


def test_check_cookies_no_cookies_returns_ok():
    mock_resp = _make_mock_response([])
    with patch("scanner.cookie_checker.requests.get", return_value=mock_resp):
        result = check_cookies(URL)
    assert result["status"] == "OK"
    assert result["total_cookies"] == 0


def test_check_cookies_connection_error():
    with patch("scanner.cookie_checker.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = check_cookies(URL)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_check_cookies_returns_expected_keys():
    mock_resp = _make_mock_response([])
    with patch("scanner.cookie_checker.requests.get", return_value=mock_resp):
        result = check_cookies(URL)
    for key in ("cookies", "issues", "total_cookies", "total_issues", "status", "error"):
        assert key in result
