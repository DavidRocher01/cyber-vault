"""
Tests for scanner/subdomain_takeover.py — all network calls are mocked.
"""

from unittest.mock import patch
import pytest

from scanner.subdomain_takeover import (
    _check_takeover,
    _fetch_body,
    _resolve_a,
    _resolve_cname,
    check_subdomain_takeover,
)

HOST = "sub.example.com"


# ---------------------------------------------------------------------------
# _resolve_cname
# ---------------------------------------------------------------------------

def test_resolve_cname_returns_target():
    mock_answer = type("A", (), {"target": "foo.github.io."})()
    with patch("scanner.subdomain_takeover.DNS_AVAILABLE", True), \
         patch("scanner.subdomain_takeover.dns.resolver.resolve", return_value=[mock_answer]):
        result = _resolve_cname(HOST)
    assert result == "foo.github.io"


def test_resolve_cname_returns_none_on_error():
    with patch("scanner.subdomain_takeover.DNS_AVAILABLE", True), \
         patch("scanner.subdomain_takeover.dns.resolver.resolve", side_effect=Exception("NXDOMAIN")):
        result = _resolve_cname(HOST)
    assert result is None


# ---------------------------------------------------------------------------
# _resolve_a
# ---------------------------------------------------------------------------

def test_resolve_a_returns_ip():
    with patch("scanner.subdomain_takeover.socket.gethostbyname", return_value="1.2.3.4"):
        result = _resolve_a(HOST)
    assert result == "1.2.3.4"


def test_resolve_a_returns_none_on_nxdomain():
    import socket
    with patch("scanner.subdomain_takeover.socket.gethostbyname", side_effect=socket.gaierror):
        result = _resolve_a(HOST)
    assert result is None


# ---------------------------------------------------------------------------
# _fetch_body
# ---------------------------------------------------------------------------

def test_fetch_body_returns_html():
    mock_resp = type("R", (), {"text": "<html>hello</html>"})()
    with patch("scanner.subdomain_takeover.requests.get", return_value=mock_resp):
        result = _fetch_body(HOST)
    assert result is not None
    assert "hello" in result


def test_fetch_body_returns_none_on_error():
    import requests as req_lib
    with patch("scanner.subdomain_takeover.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _fetch_body(HOST)
    assert result is None


# ---------------------------------------------------------------------------
# _check_takeover
# ---------------------------------------------------------------------------

def test_check_takeover_detects_nxdomain():
    with patch("scanner.subdomain_takeover._resolve_cname", return_value=None), \
         patch("scanner.subdomain_takeover._resolve_a", return_value=None):
        result = _check_takeover(HOST)
    assert result is not None
    assert result["severity"] == "CRITICAL"
    assert "NXDOMAIN" in result["reason"]


def test_check_takeover_detects_github_pages():
    with patch("scanner.subdomain_takeover._resolve_cname", return_value="myorg.github.io"), \
         patch("scanner.subdomain_takeover._resolve_a", return_value="185.199.108.153"), \
         patch("scanner.subdomain_takeover._fetch_body", return_value="There isn't a GitHub Pages site here"):
        result = _check_takeover(HOST)
    assert result is not None
    assert result["service"] == "GitHub Pages"


def test_check_takeover_returns_none_when_safe():
    with patch("scanner.subdomain_takeover._resolve_cname", return_value=None), \
         patch("scanner.subdomain_takeover._resolve_a", return_value="93.184.216.34"), \
         patch("scanner.subdomain_takeover._fetch_body", return_value="<html>Normal site</html>"):
        result = _check_takeover(HOST)
    assert result is None


# ---------------------------------------------------------------------------
# check_subdomain_takeover
# ---------------------------------------------------------------------------

def test_check_subdomain_takeover_returns_expected_keys():
    with patch("scanner.subdomain_takeover._check_takeover", return_value=None):
        result = check_subdomain_takeover(["sub.example.com"])
    for key in ("vulnerable", "total_checked", "total_vulnerable", "status", "error"):
        assert key in result


def test_check_subdomain_takeover_critical_on_finding():
    finding = {"subdomain": HOST, "cname": "foo.github.io", "service": "GitHub Pages", "reason": "Unclaimed", "severity": "CRITICAL"}
    with patch("scanner.subdomain_takeover._check_takeover", return_value=finding):
        result = check_subdomain_takeover(["sub.example.com", "api.example.com"])
    assert result["status"] == "CRITICAL"
    assert result["total_vulnerable"] == 2


def test_check_subdomain_takeover_ok_when_no_findings():
    with patch("scanner.subdomain_takeover._check_takeover", return_value=None):
        result = check_subdomain_takeover(["sub.example.com"])
    assert result["status"] == "OK"
    assert result["total_vulnerable"] == 0


def test_check_subdomain_takeover_warning_on_empty_list():
    result = check_subdomain_takeover([])
    assert result["status"] == "WARNING"
    assert result["error"] is not None
