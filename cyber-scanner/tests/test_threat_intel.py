"""
Tests for scanner/threat_intel.py — all network calls are mocked.
"""

from unittest.mock import patch
import pytest
import socket

from scanner.threat_intel import (
    _query_abuseipdb,
    _query_shodan,
    _resolve_ip,
    get_threat_intel,
)

HOST = "example.com"
IP   = "93.184.216.34"


# ---------------------------------------------------------------------------
# _resolve_ip
# ---------------------------------------------------------------------------

def test_resolve_ip_returns_address():
    with patch("scanner.threat_intel.socket.gethostbyname", return_value=IP):
        result = _resolve_ip(HOST)
    assert result == IP


def test_resolve_ip_returns_none_on_error():
    with patch("scanner.threat_intel.socket.gethostbyname", side_effect=socket.gaierror):
        result = _resolve_ip(HOST)
    assert result is None


# ---------------------------------------------------------------------------
# _query_shodan
# ---------------------------------------------------------------------------

def test_query_shodan_returns_data_on_200():
    payload = {"ports": [80, 443], "vulns": ["CVE-2021-1234"], "tags": [], "hostnames": []}
    mock_resp = type("R", (), {"status_code": 200, "json": lambda self: payload})()
    with patch("scanner.threat_intel.requests.get", return_value=mock_resp):
        result = _query_shodan(IP)
    assert result["ports"] == [80, 443]
    assert "CVE-2021-1234" in result["vulns"]


def test_query_shodan_returns_empty_dict_on_404():
    mock_resp = type("R", (), {"status_code": 404})()
    with patch("scanner.threat_intel.requests.get", return_value=mock_resp):
        result = _query_shodan(IP)
    assert result == {}


def test_query_shodan_returns_none_on_request_error():
    import requests as req_lib
    with patch("scanner.threat_intel.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _query_shodan(IP)
    assert result is None


# ---------------------------------------------------------------------------
# _query_abuseipdb
# ---------------------------------------------------------------------------

def test_query_abuseipdb_returns_data_on_200():
    payload = {"data": {"abuseConfidenceScore": 85, "totalReports": 42}}
    mock_resp = type("R", (), {"status_code": 200, "json": lambda self: payload})()
    with patch("scanner.threat_intel.requests.get", return_value=mock_resp):
        result = _query_abuseipdb(IP, "fake-key")
    assert result["abuseConfidenceScore"] == 85


def test_query_abuseipdb_returns_none_on_error():
    import requests as req_lib
    with patch("scanner.threat_intel.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _query_abuseipdb(IP, "fake-key")
    assert result is None


# ---------------------------------------------------------------------------
# get_threat_intel
# ---------------------------------------------------------------------------

def test_get_threat_intel_returns_expected_keys():
    with patch("scanner.threat_intel._resolve_ip", return_value=IP), \
         patch("scanner.threat_intel._query_shodan", return_value={}):
        result = get_threat_intel(HOST)
    for key in ("ip", "open_ports", "cves", "tags", "hostnames", "abuse_score", "abuse_reports", "status", "error"):
        assert key in result


def test_get_threat_intel_critical_on_cves():
    shodan = {"ports": [80, 443], "vulns": ["CVE-2021-44228"], "tags": [], "hostnames": []}
    with patch("scanner.threat_intel._resolve_ip", return_value=IP), \
         patch("scanner.threat_intel._query_shodan", return_value=shodan):
        result = get_threat_intel(HOST)
    assert result["status"] == "CRITICAL"
    assert "CVE-2021-44228" in result["cves"]


def test_get_threat_intel_critical_on_high_abuse_score():
    shodan = {"ports": [80], "vulns": [], "tags": [], "hostnames": []}
    abuse  = {"abuseConfidenceScore": 90, "totalReports": 100}
    with patch("scanner.threat_intel._resolve_ip", return_value=IP), \
         patch("scanner.threat_intel._query_shodan", return_value=shodan), \
         patch("scanner.threat_intel._query_abuseipdb", return_value=abuse):
        result = get_threat_intel(HOST, abuseipdb_key="fake")
    assert result["status"] == "CRITICAL"


def test_get_threat_intel_warning_on_many_ports():
    shodan = {"ports": [21, 22, 23, 25, 80, 443, 8080], "vulns": [], "tags": [], "hostnames": []}
    with patch("scanner.threat_intel._resolve_ip", return_value=IP), \
         patch("scanner.threat_intel._query_shodan", return_value=shodan):
        result = get_threat_intel(HOST)
    assert result["status"] == "WARNING"


def test_get_threat_intel_critical_on_unresolvable_hostname():
    with patch("scanner.threat_intel._resolve_ip", return_value=None):
        result = get_threat_intel("nxdomain.invalid")
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_get_threat_intel_ok_on_clean_ip():
    shodan = {"ports": [80, 443], "vulns": [], "tags": [], "hostnames": []}
    with patch("scanner.threat_intel._resolve_ip", return_value=IP), \
         patch("scanner.threat_intel._query_shodan", return_value=shodan):
        result = get_threat_intel(HOST)
    assert result["status"] == "OK"
