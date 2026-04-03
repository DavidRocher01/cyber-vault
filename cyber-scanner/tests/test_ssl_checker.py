"""
Tests for scanner.ssl_checker.check_ssl()
All network calls are mocked — no real connections are made.
"""

import ssl
import socket
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

import pytest

from scanner.ssl_checker import check_ssl


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cert(days_from_now: int) -> dict:
    """Return a minimal fake cert dict with a notAfter field."""
    future = datetime.now(timezone.utc) + timedelta(days=days_from_now)
    # Format expected by strptime: 'Nov 15 12:00:00 2025 GMT'
    not_after_str = future.strftime("%b %d %H:%M:%S %Y GMT")
    return {"notAfter": not_after_str}


def _patch_ssl_connection(cert: dict, protocol: str):
    """
    Context manager: patches socket.create_connection and ssl.SSLContext.wrap_socket
    so check_ssl() never touches the network.
    """
    mock_ssock = MagicMock()
    mock_ssock.getpeercert.return_value = cert
    mock_ssock.version.return_value = protocol
    mock_ssock.__enter__ = lambda s: s
    mock_ssock.__exit__ = MagicMock(return_value=False)

    mock_sock = MagicMock()
    mock_sock.__enter__ = lambda s: s
    mock_sock.__exit__ = MagicMock(return_value=False)

    ctx = MagicMock()
    ctx.wrap_socket.return_value = mock_ssock

    return (
        patch("socket.create_connection", return_value=mock_sock),
        patch("ssl.create_default_context", return_value=ctx),
    )


# ---------------------------------------------------------------------------
# Tests — return shape
# ---------------------------------------------------------------------------

class TestCheckSslReturnShape:
    def test_returns_expected_keys_on_success(self):
        cert = _make_cert(60)
        p1, p2 = _patch_ssl_connection(cert, "TLSv1.3")
        with p1, p2:
            result = check_ssl("example.com")

        expected_keys = {"valid", "expiry_date", "days_remaining", "protocol", "tls_ok", "status", "error"}
        assert set(result.keys()) == expected_keys

    def test_returns_expected_keys_on_error(self):
        with patch("socket.create_connection", side_effect=socket.gaierror("DNS fail")):
            result = check_ssl("nonexistent.invalid")

        expected_keys = {"valid", "expiry_date", "days_remaining", "protocol", "tls_ok", "status", "error"}
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests — error path
# ---------------------------------------------------------------------------

class TestCheckSslErrorPath:
    def test_dns_failure_sets_error_key(self):
        with patch("socket.create_connection", side_effect=socket.gaierror("Name not resolved")):
            result = check_ssl("nonexistent.invalid")

        assert result["error"] is not None
        assert "DNS" in result["error"]
        assert result["status"] == "CRITICAL"
        assert result["valid"] is False

    def test_connection_refused_sets_error_key(self):
        with patch("socket.create_connection", side_effect=ConnectionRefusedError()):
            result = check_ssl("example.com")

        assert result["error"] is not None
        assert result["status"] == "CRITICAL"

    def test_timeout_sets_error_key(self):
        with patch("socket.create_connection", side_effect=socket.timeout()):
            result = check_ssl("example.com")

        assert result["error"] is not None
        assert result["status"] == "CRITICAL"

    def test_ssl_verification_error_sets_error_key(self):
        with patch("socket.create_connection", side_effect=ssl.SSLCertVerificationError("bad cert")):
            result = check_ssl("example.com")

        assert result["error"] is not None
        assert result["status"] == "CRITICAL"


# ---------------------------------------------------------------------------
# Tests — status logic
# ---------------------------------------------------------------------------

class TestCheckSslStatusLogic:
    def test_valid_cert_long_expiry_tls13_is_ok(self):
        cert = _make_cert(90)
        p1, p2 = _patch_ssl_connection(cert, "TLSv1.3")
        with p1, p2:
            result = check_ssl("example.com")

        assert result["status"] == "OK"
        assert result["valid"] is True
        assert result["tls_ok"] is True

    def test_valid_cert_short_expiry_under_7_days_is_critical(self):
        cert = _make_cert(5)
        p1, p2 = _patch_ssl_connection(cert, "TLSv1.3")
        with p1, p2:
            result = check_ssl("example.com")

        assert result["status"] == "CRITICAL"

    def test_valid_cert_expiry_between_7_and_30_is_warning(self):
        cert = _make_cert(15)
        p1, p2 = _patch_ssl_connection(cert, "TLSv1.3")
        with p1, p2:
            result = check_ssl("example.com")

        assert result["status"] == "WARNING"

    def test_outdated_tls_overrides_status_to_critical(self):
        """Even with a valid cert expiring in 90 days, bad TLS = CRITICAL."""
        cert = _make_cert(90)
        p1, p2 = _patch_ssl_connection(cert, "TLSv1.0")
        with p1, p2:
            result = check_ssl("example.com")

        assert result["tls_ok"] is False
        assert result["status"] == "CRITICAL"

    def test_tls12_is_acceptable(self):
        cert = _make_cert(60)
        p1, p2 = _patch_ssl_connection(cert, "TLSv1.2")
        with p1, p2:
            result = check_ssl("example.com")

        assert result["tls_ok"] is True
        assert result["status"] == "OK"
