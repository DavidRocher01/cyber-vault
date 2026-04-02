"""
Tests for scanner/email_checker.py — all DNS calls are mocked.
"""

from unittest.mock import patch, MagicMock
import pytest
import dns.exception

from scanner.email_checker import (
    _check_spf,
    _check_dkim,
    _check_dmarc,
    _query_txt,
    check_email_security,
)

DOMAIN = "example.com"


# ---------------------------------------------------------------------------
# _query_txt
# ---------------------------------------------------------------------------

def test_query_txt_returns_strings_on_success():
    mock_rdata = MagicMock()
    mock_rdata.strings = [b"v=spf1 -all"]
    mock_answer = [mock_rdata]
    with patch("scanner.email_checker.dns.resolver.resolve", return_value=mock_answer):
        result = _query_txt(DOMAIN)
    assert result == ["v=spf1 -all"]


def test_query_txt_returns_empty_on_dns_error():
    with patch("scanner.email_checker.dns.resolver.resolve", side_effect=dns.exception.DNSException):
        result = _query_txt(DOMAIN)
    assert result == []


# ---------------------------------------------------------------------------
# _check_spf
# ---------------------------------------------------------------------------

def test_check_spf_found_strict():
    with patch("scanner.email_checker._query_txt", return_value=["v=spf1 include:_spf.google.com -all"]):
        result = _check_spf(DOMAIN)
    assert result["found"] is True
    assert result["strict"] is True


def test_check_spf_found_not_strict():
    with patch("scanner.email_checker._query_txt", return_value=["v=spf1 include:_spf.google.com ~all"]):
        result = _check_spf(DOMAIN)
    assert result["found"] is True
    assert result["strict"] is False


def test_check_spf_not_found():
    with patch("scanner.email_checker._query_txt", return_value=["some other record"]):
        result = _check_spf(DOMAIN)
    assert result["found"] is False


# ---------------------------------------------------------------------------
# _check_dkim
# ---------------------------------------------------------------------------

def test_check_dkim_found_with_google_selector():
    def fake_query(name):
        if "google._domainkey" in name:
            return ["v=DKIM1; k=rsa; p=MIGfMA0..."]
        return []
    with patch("scanner.email_checker._query_txt", side_effect=fake_query):
        result = _check_dkim(DOMAIN)
    assert result["found"] is True
    assert result["selector"] == "google"


def test_check_dkim_not_found():
    with patch("scanner.email_checker._query_txt", return_value=[]):
        result = _check_dkim(DOMAIN)
    assert result["found"] is False
    assert result["selector"] is None


# ---------------------------------------------------------------------------
# _check_dmarc
# ---------------------------------------------------------------------------

def test_check_dmarc_found_reject_policy():
    with patch("scanner.email_checker._query_txt", return_value=["v=DMARC1; p=reject; rua=mailto:dmarc@example.com"]):
        result = _check_dmarc(DOMAIN)
    assert result["found"] is True
    assert result["policy"] == "reject"


def test_check_dmarc_found_none_policy():
    with patch("scanner.email_checker._query_txt", return_value=["v=DMARC1; p=none"]):
        result = _check_dmarc(DOMAIN)
    assert result["found"] is True
    assert result["policy"] == "none"


def test_check_dmarc_not_found():
    with patch("scanner.email_checker._query_txt", return_value=[]):
        result = _check_dmarc(DOMAIN)
    assert result["found"] is False


# ---------------------------------------------------------------------------
# check_email_security
# ---------------------------------------------------------------------------

def test_check_email_security_all_ok():
    with patch("scanner.email_checker._check_spf", return_value={"found": True, "record": "v=spf1 -all", "strict": True}), \
         patch("scanner.email_checker._check_dkim", return_value={"found": True, "selector": "google"}), \
         patch("scanner.email_checker._check_dmarc", return_value={"found": True, "record": "v=DMARC1; p=reject", "policy": "reject"}):
        result = check_email_security(DOMAIN)
    assert result["status"] == "OK"
    assert result["issues"] == []


def test_check_email_security_critical_when_all_missing():
    with patch("scanner.email_checker._check_spf", return_value={"found": False, "record": None, "strict": False}), \
         patch("scanner.email_checker._check_dkim", return_value={"found": False, "selector": None}), \
         patch("scanner.email_checker._check_dmarc", return_value={"found": False, "record": None, "policy": None}):
        result = check_email_security(DOMAIN)
    assert result["status"] == "CRITICAL"
    assert len(result["issues"]) == 3


def test_check_email_security_warning_when_dmarc_none_policy():
    with patch("scanner.email_checker._check_spf", return_value={"found": True, "record": "v=spf1 -all", "strict": True}), \
         patch("scanner.email_checker._check_dkim", return_value={"found": True, "selector": "default"}), \
         patch("scanner.email_checker._check_dmarc", return_value={"found": True, "record": "v=DMARC1; p=none", "policy": "none"}):
        result = check_email_security(DOMAIN)
    assert result["status"] == "WARNING"


def test_check_email_security_warning_when_spf_not_strict():
    with patch("scanner.email_checker._check_spf", return_value={"found": True, "record": "v=spf1 ~all", "strict": False}), \
         patch("scanner.email_checker._check_dkim", return_value={"found": True, "selector": "google"}), \
         patch("scanner.email_checker._check_dmarc", return_value={"found": True, "record": "v=DMARC1; p=reject", "policy": "reject"}):
        result = check_email_security(DOMAIN)
    assert result["status"] == "WARNING"


def test_check_email_security_returns_expected_keys():
    with patch("scanner.email_checker._check_spf", return_value={"found": True, "record": "", "strict": True}), \
         patch("scanner.email_checker._check_dkim", return_value={"found": True, "selector": "mail"}), \
         patch("scanner.email_checker._check_dmarc", return_value={"found": True, "record": "", "policy": "quarantine"}):
        result = check_email_security(DOMAIN)
    for key in ("spf", "dkim", "dmarc", "issues", "status", "error"):
        assert key in result
