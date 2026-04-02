"""
Tests for scanner/breach_checker.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.breach_checker import (
    _check_email,
    _check_domain,
    check_breach,
)

API_KEY = "test-api-key-123"
EMAIL = "test@example.com"
DOMAIN = "example.com"


# ---------------------------------------------------------------------------
# _check_email
# ---------------------------------------------------------------------------

def test_check_email_no_breaches():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("scanner.breach_checker.requests.get", return_value=mock_resp):
        result = _check_email(EMAIL, API_KEY)
    assert result["total"] == 0
    assert result["breaches"] == []


def test_check_email_returns_breaches():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = [
        {"Name": "Adobe", "Domain": "adobe.com", "BreachDate": "2013-10-04",
         "PwnCount": 152445165, "DataClasses": ["Email addresses", "Passwords"]}
    ]
    mock_resp.raise_for_status = MagicMock()
    with patch("scanner.breach_checker.requests.get", return_value=mock_resp):
        result = _check_email(EMAIL, API_KEY)
    assert result["total"] == 1
    assert result["breaches"][0]["name"] == "Adobe"


def test_check_email_invalid_api_key():
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    with patch("scanner.breach_checker.requests.get", return_value=mock_resp):
        result = _check_email(EMAIL, API_KEY)
    assert "error" in result
    assert "Invalid" in result["error"]


# ---------------------------------------------------------------------------
# _check_domain
# ---------------------------------------------------------------------------

def test_check_domain_no_breaches():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    with patch("scanner.breach_checker.requests.get", return_value=mock_resp):
        result = _check_domain(DOMAIN, API_KEY)
    assert result["total"] == 0


def test_check_domain_returns_accounts():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "john@example.com": ["Adobe", "LinkedIn"],
        "jane@example.com": ["Adobe"],
    }
    mock_resp.raise_for_status = MagicMock()
    with patch("scanner.breach_checker.requests.get", return_value=mock_resp):
        result = _check_domain(DOMAIN, API_KEY)
    assert result["total"] == 2


def test_check_domain_requires_paid_key():
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    with patch("scanner.breach_checker.requests.get", return_value=mock_resp):
        result = _check_domain(DOMAIN, API_KEY)
    assert "error" in result
    assert "paid" in result["error"].lower()


# ---------------------------------------------------------------------------
# check_breach
# ---------------------------------------------------------------------------

def test_check_breach_warning_when_no_api_key():
    result = check_breach(EMAIL)
    assert result["status"] == "WARNING"
    assert "API key" in result["error"]


def test_check_breach_ok_no_breaches():
    with patch("scanner.breach_checker._check_email", return_value={"breaches": [], "total": 0}):
        result = check_breach(EMAIL, api_key=API_KEY, mode="email")
    assert result["status"] == "OK"
    assert result["total"] == 0


def test_check_breach_warning_one_breach():
    breach = {"name": "Adobe", "domain": "adobe.com", "breach_date": "2013-10-04",
              "pwn_count": 152000000, "data_classes": ["Emails", "Passwords"]}
    with patch("scanner.breach_checker._check_email", return_value={"breaches": [breach], "total": 1}):
        result = check_breach(EMAIL, api_key=API_KEY, mode="email")
    assert result["status"] == "WARNING"


def test_check_breach_critical_three_or_more_breaches():
    breaches = [{"name": f"Site{i}", "domain": "", "breach_date": "", "pwn_count": 1000, "data_classes": []} for i in range(3)]
    with patch("scanner.breach_checker._check_email", return_value={"breaches": breaches, "total": 3}):
        result = check_breach(EMAIL, api_key=API_KEY, mode="email")
    assert result["status"] == "CRITICAL"


def test_check_breach_handles_api_error():
    with patch("scanner.breach_checker._check_email", return_value={"error": "Rate limited"}):
        result = check_breach(EMAIL, api_key=API_KEY, mode="email")
    assert result["status"] == "CRITICAL"
    assert result["error"] == "Rate limited"


def test_check_breach_returns_expected_keys():
    with patch("scanner.breach_checker._check_email", return_value={"breaches": [], "total": 0}):
        result = check_breach(EMAIL, api_key=API_KEY, mode="email")
    for key in ("target", "mode", "breaches", "accounts", "total", "status", "error"):
        assert key in result
