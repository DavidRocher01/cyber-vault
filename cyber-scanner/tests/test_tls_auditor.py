"""
Tests for scanner/tls_auditor.py — all network calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest

from scanner.tls_auditor import (
    _check_hsts,
    _find_weak_ciphers,
    _get_certificate_details,
    _get_supported_protocols,
    audit_tls,
)

HOST = "example.com"


# ---------------------------------------------------------------------------
# _get_supported_protocols
# ---------------------------------------------------------------------------

def test_get_supported_protocols_returns_supported_version():
    mock_sock = MagicMock()
    mock_tls  = MagicMock()
    mock_sock.__enter__ = lambda s: mock_sock
    mock_sock.__exit__  = MagicMock(return_value=False)
    mock_tls.__enter__  = lambda s: mock_tls
    mock_tls.__exit__   = MagicMock(return_value=False)

    with patch("scanner.tls_auditor.socket.create_connection", return_value=mock_sock), \
         patch("scanner.tls_auditor.ssl.SSLContext") as mock_ctx_cls:
        mock_ctx = MagicMock()
        mock_ctx.wrap_socket.return_value = mock_tls
        mock_ctx_cls.return_value = mock_ctx
        result = _get_supported_protocols(HOST)
    assert isinstance(result, list)


def test_get_supported_protocols_returns_empty_on_all_errors():
    with patch("scanner.tls_auditor.socket.create_connection", side_effect=OSError):
        result = _get_supported_protocols(HOST)
    assert result == []


# ---------------------------------------------------------------------------
# _get_certificate_details
# ---------------------------------------------------------------------------

def test_get_certificate_details_returns_dict_on_success():
    mock_sock = MagicMock()
    mock_tls  = MagicMock()
    mock_sock.__enter__ = lambda s: mock_sock
    mock_sock.__exit__  = MagicMock(return_value=False)
    mock_tls.__enter__  = lambda s: mock_tls
    mock_tls.__exit__   = MagicMock(return_value=False)
    mock_tls.getpeercert.return_value = {
        "subject":        [(("commonName", "example.com"),)],
        "issuer":         [(("organizationName", "Let's Encrypt"),)],
        "subjectAltName": [("DNS", "example.com"), ("DNS", "www.example.com")],
        "notAfter":       "May 14 00:00:00 2026 GMT",
    }

    with patch("scanner.tls_auditor.socket.create_connection", return_value=mock_sock), \
         patch("scanner.tls_auditor.ssl.create_default_context") as mock_ctx_cls:
        mock_ctx = MagicMock()
        mock_ctx.wrap_socket.return_value = mock_tls
        mock_ctx_cls.return_value = mock_ctx
        result = _get_certificate_details(HOST)

    assert result is not None
    assert result["subject"] == "example.com"
    assert "example.com" in result["sans"]


def test_get_certificate_details_returns_none_on_error():
    with patch("scanner.tls_auditor.socket.create_connection", side_effect=OSError):
        result = _get_certificate_details(HOST)
    assert result is None


# ---------------------------------------------------------------------------
# _check_hsts
# ---------------------------------------------------------------------------

def test_check_hsts_detects_hsts_header():
    mock_resp = MagicMock()
    mock_resp.headers = {"Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload"}
    with patch("scanner.tls_auditor.requests.get", return_value=mock_resp):
        result = _check_hsts(HOST)
    assert result["present"] is True
    assert result["max_age"] == 31536000
    assert result["preload"] is True
    assert result["include_subdomains"] is True


def test_check_hsts_absent_when_no_header():
    mock_resp = MagicMock()
    mock_resp.headers = {}
    with patch("scanner.tls_auditor.requests.get", return_value=mock_resp):
        result = _check_hsts(HOST)
    assert result["present"] is False
    assert result["max_age"] == 0


# ---------------------------------------------------------------------------
# _find_weak_ciphers
# ---------------------------------------------------------------------------

def test_find_weak_ciphers_detects_rc4():
    mock_sock = MagicMock()
    mock_tls  = MagicMock()
    mock_sock.__enter__ = lambda s: mock_sock
    mock_sock.__exit__  = MagicMock(return_value=False)
    mock_tls.__enter__  = lambda s: mock_tls
    mock_tls.__exit__   = MagicMock(return_value=False)
    mock_tls.cipher.return_value = ("RC4-MD5", "TLSv1.2", 128)

    with patch("scanner.tls_auditor.socket.create_connection", return_value=mock_sock), \
         patch("scanner.tls_auditor.ssl.SSLContext") as mock_ctx_cls:
        mock_ctx = MagicMock()
        mock_ctx.wrap_socket.return_value = mock_tls
        mock_ctx_cls.return_value = mock_ctx
        result = _find_weak_ciphers(HOST)
    assert "RC4-MD5" in result


def test_find_weak_ciphers_returns_empty_on_error():
    with patch("scanner.tls_auditor.socket.create_connection", side_effect=OSError):
        result = _find_weak_ciphers(HOST)
    assert result == []


# ---------------------------------------------------------------------------
# audit_tls
# ---------------------------------------------------------------------------

def test_audit_tls_returns_expected_keys():
    with patch("scanner.tls_auditor._get_supported_protocols", return_value=["TLSv1.2", "TLSv1.3"]), \
         patch("scanner.tls_auditor._get_certificate_details", return_value=None), \
         patch("scanner.tls_auditor._check_hsts", return_value={"present": True, "max_age": 31536000, "preload": True, "include_subdomains": True}), \
         patch("scanner.tls_auditor._find_weak_ciphers", return_value=[]):
        result = audit_tls(HOST)
    for key in ("supported_protocols", "weak_protocols", "certificate", "hsts", "weak_ciphers", "status", "error"):
        assert key in result


def test_audit_tls_critical_on_weak_protocols():
    with patch("scanner.tls_auditor._get_supported_protocols", return_value=["TLSv1.0", "TLSv1.1", "TLSv1.2"]), \
         patch("scanner.tls_auditor._get_certificate_details", return_value=None), \
         patch("scanner.tls_auditor._check_hsts", return_value={"present": True, "max_age": 300, "preload": False, "include_subdomains": False}), \
         patch("scanner.tls_auditor._find_weak_ciphers", return_value=[]):
        result = audit_tls(HOST)
    assert result["status"] == "CRITICAL"
    assert "TLSv1.0" in result["weak_protocols"]


def test_audit_tls_warning_on_missing_hsts():
    with patch("scanner.tls_auditor._get_supported_protocols", return_value=["TLSv1.2", "TLSv1.3"]), \
         patch("scanner.tls_auditor._get_certificate_details", return_value=None), \
         patch("scanner.tls_auditor._check_hsts", return_value={"present": False, "max_age": 0, "preload": False, "include_subdomains": False}), \
         patch("scanner.tls_auditor._find_weak_ciphers", return_value=[]):
        result = audit_tls(HOST)
    assert result["status"] == "WARNING"


def test_audit_tls_ok_on_clean_config():
    with patch("scanner.tls_auditor._get_supported_protocols", return_value=["TLSv1.2", "TLSv1.3"]), \
         patch("scanner.tls_auditor._get_certificate_details", return_value=None), \
         patch("scanner.tls_auditor._check_hsts", return_value={"present": True, "max_age": 31536000, "preload": True, "include_subdomains": True}), \
         patch("scanner.tls_auditor._find_weak_ciphers", return_value=[]):
        result = audit_tls(HOST)
    assert result["status"] == "OK"


def test_audit_tls_critical_on_exception():
    with patch("scanner.tls_auditor._get_supported_protocols", side_effect=RuntimeError("boom")):
        result = audit_tls(HOST)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None
