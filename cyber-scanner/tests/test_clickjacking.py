"""
Tests for scanner/clickjacking.py — all HTTP calls are mocked.
"""

from unittest.mock import patch
import pytest
import requests as req_lib

from scanner.clickjacking import (
    _check_csp_frame_ancestors,
    _check_xfo,
    _fetch_headers,
    check_clickjacking,
)

URL = "https://example.com"


# ---------------------------------------------------------------------------
# _fetch_headers
# ---------------------------------------------------------------------------

def test_fetch_headers_returns_lowercased_dict():
    mock_resp = type("R", (), {"headers": {"X-Frame-Options": "DENY", "Server": "nginx"}, "status_code": 200})()
    with patch("scanner.clickjacking.requests.get", return_value=mock_resp):
        result = _fetch_headers(URL)
    assert result is not None
    assert "x-frame-options" in result
    assert result["x-frame-options"] == "DENY"


def test_fetch_headers_returns_none_on_error():
    with patch("scanner.clickjacking.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _fetch_headers(URL)
    assert result is None


# ---------------------------------------------------------------------------
# _check_xfo
# ---------------------------------------------------------------------------

def test_check_xfo_protected_on_deny():
    result = _check_xfo({"x-frame-options": "DENY"})
    assert result["present"] is True
    assert result["protected"] is True


def test_check_xfo_protected_on_sameorigin():
    result = _check_xfo({"x-frame-options": "SAMEORIGIN"})
    assert result["protected"] is True


def test_check_xfo_not_protected_on_allow_from():
    result = _check_xfo({"x-frame-options": "ALLOW-FROM https://trusted.com"})
    assert result["present"] is True
    assert result["protected"] is False


def test_check_xfo_absent():
    result = _check_xfo({})
    assert result["present"] is False
    assert result["protected"] is False


# ---------------------------------------------------------------------------
# _check_csp_frame_ancestors
# ---------------------------------------------------------------------------

def test_check_csp_frame_ancestors_protected_on_none():
    headers = {"content-security-policy": "default-src 'self'; frame-ancestors 'none'"}
    result = _check_csp_frame_ancestors(headers)
    assert result["present"] is True
    assert result["protected"] is True


def test_check_csp_frame_ancestors_protected_on_self():
    headers = {"content-security-policy": "frame-ancestors 'self'"}
    result = _check_csp_frame_ancestors(headers)
    assert result["protected"] is True


def test_check_csp_frame_ancestors_not_protected_on_wildcard():
    headers = {"content-security-policy": "frame-ancestors *"}
    result = _check_csp_frame_ancestors(headers)
    assert result["present"] is True
    assert result["protected"] is False


def test_check_csp_frame_ancestors_absent():
    result = _check_csp_frame_ancestors({"content-security-policy": "default-src 'self'"})
    assert result["present"] is False


# ---------------------------------------------------------------------------
# check_clickjacking
# ---------------------------------------------------------------------------

def test_check_clickjacking_returns_expected_keys():
    headers = {"x-frame-options": "DENY"}
    with patch("scanner.clickjacking._fetch_headers", return_value=headers):
        result = check_clickjacking(URL)
    for key in ("vulnerable", "xfo", "csp_frame_ancestors", "status", "error"):
        assert key in result


def test_check_clickjacking_ok_when_both_protected():
    headers = {
        "x-frame-options": "DENY",
        "content-security-policy": "frame-ancestors 'none'",
    }
    with patch("scanner.clickjacking._fetch_headers", return_value=headers):
        result = check_clickjacking(URL)
    assert result["vulnerable"] is False
    assert result["status"] == "OK"


def test_check_clickjacking_critical_when_no_headers():
    with patch("scanner.clickjacking._fetch_headers", return_value={}):
        result = check_clickjacking(URL)
    assert result["vulnerable"] is True
    assert result["status"] == "CRITICAL"


def test_check_clickjacking_critical_on_fetch_failure():
    with patch("scanner.clickjacking._fetch_headers", return_value=None):
        result = check_clickjacking(URL)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None
