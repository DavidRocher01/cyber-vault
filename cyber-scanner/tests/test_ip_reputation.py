"""
Tests for scanner/ip_reputation.py — all DNS and socket calls are mocked.
"""

from unittest.mock import patch, MagicMock
import pytest
import dns.exception

from scanner.ip_reputation import (
    _reverse_ip,
    _resolve_hostname,
    _query_dnsbl,
    check_ip_reputation,
)


# ---------------------------------------------------------------------------
# _reverse_ip
# ---------------------------------------------------------------------------

def test_reverse_ip_standard():
    assert _reverse_ip("1.2.3.4") == "4.3.2.1"


def test_reverse_ip_with_zeros():
    assert _reverse_ip("192.168.0.1") == "1.0.168.192"


# ---------------------------------------------------------------------------
# _resolve_hostname
# ---------------------------------------------------------------------------

def test_resolve_hostname_success():
    with patch("scanner.ip_reputation.socket.gethostbyname", return_value="93.184.216.34"):
        result = _resolve_hostname("example.com")
    assert result == "93.184.216.34"


def test_resolve_hostname_failure():
    import socket
    with patch("scanner.ip_reputation.socket.gethostbyname", side_effect=socket.gaierror):
        result = _resolve_hostname("nonexistent.invalid")
    assert result is None


# ---------------------------------------------------------------------------
# _query_dnsbl
# ---------------------------------------------------------------------------

def test_query_dnsbl_listed():
    mock_answer = MagicMock()
    with patch("scanner.ip_reputation.dns.resolver.resolve", return_value=mock_answer):
        result = _query_dnsbl("4.3.2.1", "zen.spamhaus.org")
    assert result is True


def test_query_dnsbl_not_listed():
    with patch("scanner.ip_reputation.dns.resolver.resolve", side_effect=dns.exception.DNSException):
        result = _query_dnsbl("4.3.2.1", "zen.spamhaus.org")
    assert result is False


# ---------------------------------------------------------------------------
# check_ip_reputation
# ---------------------------------------------------------------------------

def test_check_ip_reputation_ok_clean_ip():
    with patch("scanner.ip_reputation._resolve_hostname", return_value="93.184.216.34"), \
         patch("scanner.ip_reputation._query_dnsbl", return_value=False):
        result = check_ip_reputation("example.com")
    assert result["status"] == "OK"
    assert result["total_listed"] == 0
    assert result["ip"] == "93.184.216.34"


def test_check_ip_reputation_warning_one_blacklist():
    call_count = 0
    def fake_dnsbl(rev_ip, host):
        nonlocal call_count
        call_count += 1
        return call_count == 1  # only first call returns True

    with patch("scanner.ip_reputation._resolve_hostname", return_value="1.2.3.4"), \
         patch("scanner.ip_reputation._query_dnsbl", side_effect=fake_dnsbl):
        result = check_ip_reputation("badhost.com")
    assert result["status"] == "WARNING"
    assert result["total_listed"] == 1


def test_check_ip_reputation_critical_two_or_more_blacklists():
    with patch("scanner.ip_reputation._resolve_hostname", return_value="1.2.3.4"), \
         patch("scanner.ip_reputation._query_dnsbl", return_value=True):
        result = check_ip_reputation("spammer.com")
    assert result["status"] == "CRITICAL"
    assert result["total_listed"] >= 2


def test_check_ip_reputation_hostname_unresolvable():
    with patch("scanner.ip_reputation._resolve_hostname", return_value=None):
        result = check_ip_reputation("nonexistent.invalid")
    assert result["status"] == "CRITICAL"
    assert "resolve" in result["error"].lower()


def test_check_ip_reputation_skips_private_ip():
    with patch("scanner.ip_reputation._resolve_hostname", return_value="192.168.1.1"):
        result = check_ip_reputation("localhost")
    assert result["status"] == "OK"
    assert "private" in result["error"].lower()


def test_check_ip_reputation_returns_expected_keys():
    with patch("scanner.ip_reputation._resolve_hostname", return_value="93.184.216.34"), \
         patch("scanner.ip_reputation._query_dnsbl", return_value=False):
        result = check_ip_reputation("example.com")
    for key in ("ip", "listed_in", "total_listed", "status", "error"):
        assert key in result
