"""
Tests for scanner/dns_scanner.py — all DNS and socket calls are mocked.
"""

import socket
from unittest.mock import MagicMock, patch

import dns.exception
import pytest

from scanner.dns_scanner import (
    _resolve,
    _try_zone_transfer,
    scan_subdomains,
)

DOMAIN = "example.com"


# ---------------------------------------------------------------------------
# _resolve
# ---------------------------------------------------------------------------

def test_resolve_returns_ip_on_success():
    with patch("scanner.dns_scanner.socket.gethostbyname", return_value="93.184.216.34"):
        assert _resolve("www.example.com") == "93.184.216.34"


def test_resolve_returns_none_on_failure():
    with patch("scanner.dns_scanner.socket.gethostbyname", side_effect=socket.gaierror):
        assert _resolve("nonexistent.example.com") is None


# ---------------------------------------------------------------------------
# _try_zone_transfer
# ---------------------------------------------------------------------------

def test_zone_transfer_vulnerable():
    mock_ns = MagicMock()
    mock_ns.target = "ns1.example.com."
    mock_zone = MagicMock()
    mock_zone.nodes.keys.return_value = ["@", "www", "mail"]
    with patch("scanner.dns_scanner.dns.resolver.resolve", return_value=[mock_ns]), \
         patch("scanner.dns_scanner._resolve", return_value="1.2.3.4"), \
         patch("scanner.dns_scanner.dns.zone.from_xfr", return_value=mock_zone), \
         patch("scanner.dns_scanner.dns.query.xfr", return_value=iter([])):
        result = _try_zone_transfer(DOMAIN)
    assert result["vulnerable"] is True
    assert len(result["records_found"]) > 0


def test_zone_transfer_not_vulnerable():
    mock_ns = MagicMock()
    mock_ns.target = "ns1.example.com."
    with patch("scanner.dns_scanner.dns.resolver.resolve", return_value=[mock_ns]), \
         patch("scanner.dns_scanner._resolve", return_value="1.2.3.4"), \
         patch("scanner.dns_scanner.dns.zone.from_xfr", side_effect=Exception("AXFR refused")), \
         patch("scanner.dns_scanner.dns.query.xfr", return_value=iter([])):
        result = _try_zone_transfer(DOMAIN)
    assert result["vulnerable"] is False


def test_zone_transfer_ns_resolution_fails():
    with patch("scanner.dns_scanner.dns.resolver.resolve", side_effect=dns.exception.DNSException):
        result = _try_zone_transfer(DOMAIN)
    assert result["vulnerable"] is False
    assert result["nameservers"] == []


# ---------------------------------------------------------------------------
# scan_subdomains
# ---------------------------------------------------------------------------

def test_scan_subdomains_finds_live_subdomains():
    def fake_resolve(hostname):
        return "1.2.3.4" if hostname.startswith("www.") else None
    with patch("scanner.dns_scanner._resolve", side_effect=fake_resolve), \
         patch("scanner.dns_scanner._try_zone_transfer", return_value={"vulnerable": False, "nameservers": [], "records_found": []}):
        result = scan_subdomains(DOMAIN)
    assert result["total_found"] == 1
    assert result["found"][0]["subdomain"] == "www.example.com"


def test_scan_subdomains_ok_when_few_found():
    def fake_resolve(hostname):
        return "1.2.3.4" if hostname.startswith("www.") else None
    with patch("scanner.dns_scanner._resolve", side_effect=fake_resolve), \
         patch("scanner.dns_scanner._try_zone_transfer", return_value={"vulnerable": False, "nameservers": [], "records_found": []}):
        result = scan_subdomains(DOMAIN)
    assert result["status"] == "OK"


def test_scan_subdomains_warning_when_many_found():
    with patch("scanner.dns_scanner._resolve", return_value="1.2.3.4"), \
         patch("scanner.dns_scanner._try_zone_transfer", return_value={"vulnerable": False, "nameservers": [], "records_found": []}):
        result = scan_subdomains(DOMAIN)
    assert result["status"] in ("WARNING", "CRITICAL")
    assert result["total_found"] >= 5


def test_scan_subdomains_critical_on_zone_transfer():
    with patch("scanner.dns_scanner._resolve", return_value=None), \
         patch("scanner.dns_scanner._try_zone_transfer", return_value={"vulnerable": True, "nameservers": ["ns1.example.com"], "records_found": ["www", "mail"]}):
        result = scan_subdomains(DOMAIN)
    assert result["status"] == "CRITICAL"


def test_scan_subdomains_returns_expected_keys():
    with patch("scanner.dns_scanner._resolve", return_value=None), \
         patch("scanner.dns_scanner._try_zone_transfer", return_value={"vulnerable": False, "nameservers": [], "records_found": []}):
        result = scan_subdomains(DOMAIN)
    for key in ("found", "total_found", "zone_transfer", "status", "error"):
        assert key in result
