"""
Unit tests — SSRF protection (app/core/ssrf.py).

Tests _is_private() and assert_no_ssrf() without making real network calls.
"""

import socket
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.core.ssrf import _is_private, assert_no_ssrf


# ── _is_private() ─────────────────────────────────────────────────────────────

class TestIsPrivate:
    def test_loopback_is_private(self):
        assert _is_private("127.0.0.1") is True

    def test_localhost_ipv6_is_private(self):
        assert _is_private("::1") is True

    def test_rfc1918_10_is_private(self):
        assert _is_private("10.0.0.1") is True

    def test_rfc1918_172_is_private(self):
        assert _is_private("172.16.0.1") is True

    def test_rfc1918_192_168_is_private(self):
        assert _is_private("192.168.1.1") is True

    def test_link_local_is_private(self):
        assert _is_private("169.254.0.1") is True

    def test_cgnat_is_private(self):
        assert _is_private("100.64.0.1") is True

    def test_fc_ipv6_is_private(self):
        assert _is_private("fc00::1") is True

    def test_fe80_ipv6_is_private(self):
        assert _is_private("fe80::1") is True

    def test_public_ip_is_not_private(self):
        assert _is_private("1.1.1.1") is False

    def test_another_public_ip(self):
        assert _is_private("8.8.8.8") is False

    def test_unparseable_ip_blocked(self):
        assert _is_private("not-an-ip") is True


# ── assert_no_ssrf() ──────────────────────────────────────────────────────────

class TestAssertNoSsrf:
    def test_valid_public_url_passes(self):
        with patch("app.core.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("1.1.1.1", 0))]
            assert_no_ssrf("https://example.com")  # must not raise

    def test_private_ip_raises_422(self):
        with patch("app.core.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("192.168.1.1", 0))]
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://internal.local")
            assert exc.value.status_code == 422
            assert "privée" in exc.value.detail

    def test_loopback_raises_422(self):
        with patch("app.core.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("127.0.0.1", 0))]
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://localhost")
            assert exc.value.status_code == 422

    def test_dns_failure_raises_422(self):
        with patch("app.core.ssrf.socket.getaddrinfo", side_effect=socket.gaierror("nxdomain")):
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://nonexistent.invalid")
            assert exc.value.status_code == 422
            assert "résoudre" in exc.value.detail

    def test_missing_hostname_raises_422(self):
        with pytest.raises(HTTPException) as exc:
            assert_no_ssrf("https://")
        assert exc.value.status_code == 422
        assert "hôte" in exc.value.detail

    def test_multiple_addrs_all_must_be_public(self):
        """If any resolved IP is private, the request is blocked."""
        with patch("app.core.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [
                (None, None, None, None, ("1.1.1.1", 0)),
                (None, None, None, None, ("10.0.0.1", 0)),
            ]
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://mixed.example.com")
            assert exc.value.status_code == 422

    def test_aws_imds_link_local_blocked(self):
        with patch("app.core.ssrf.socket.getaddrinfo") as mock_dns:
            mock_dns.return_value = [(None, None, None, None, ("169.254.169.254", 0))]
            with pytest.raises(HTTPException) as exc:
                assert_no_ssrf("https://metadata.aws")
            assert exc.value.status_code == 422
