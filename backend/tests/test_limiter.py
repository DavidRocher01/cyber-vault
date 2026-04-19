"""
Unit tests — app.core.limiter._get_real_ip

Verifies correct IP extraction for all proxy configurations and spoofing scenarios.
"""
from unittest.mock import MagicMock, patch

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from app.core.limiter import _get_real_ip, _is_public_ip


# ── _is_public_ip ─────────────────────────────────────────────────────────────

class TestIsPublicIp:
    def test_public_ipv4(self):
        assert _is_public_ip("1.2.3.4") is True

    def test_private_10(self):
        assert _is_public_ip("10.0.0.1") is False

    def test_private_192168(self):
        assert _is_public_ip("192.168.1.1") is False

    def test_private_172_16(self):
        assert _is_public_ip("172.16.0.1") is False

    def test_loopback(self):
        assert _is_public_ip("127.0.0.1") is False

    def test_link_local(self):
        assert _is_public_ip("169.254.169.254") is False

    def test_invalid(self):
        assert _is_public_ip("not-an-ip") is False

    def test_public_ipv6(self):
        assert _is_public_ip("2001:db8::1") is False  # documentation range → reserved

    def test_real_public_ipv6(self):
        assert _is_public_ip("2607:f8b0:4004:c08::65") is True


# ── _get_real_ip helpers ───────────────────────────────────────────────────────

def _make_request(xff: str | None, client_host: str = "10.0.1.100") -> Request:
    """Build a minimal fake Request with the given X-Forwarded-For header."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (b"x-forwarded-for", xff.encode()) if xff is not None else (b"host", b"localhost"),
        ],
        "client": (client_host, 12345),
    }
    return Request(scope)


# ── _get_real_ip — no proxy (TRUSTED_PROXY_COUNT=0) ──────────────────────────

class TestGetRealIpNoproxy:
    def test_no_xff_uses_client_host(self):
        req = _make_request(None, client_host="5.6.7.8")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 0
            ip = _get_real_ip(req)
        assert ip == "5.6.7.8"

    def test_xff_present_but_zero_proxies_returns_last_xff(self):
        """With 0 trusted proxies, we fall back to the last XFF entry."""
        req = _make_request("1.2.3.4")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 0
            ip = _get_real_ip(req)
        assert ip == "1.2.3.4"


# ── _get_real_ip — one proxy / ALB only (TRUSTED_PROXY_COUNT=1) ───────────────

class TestGetRealIpOneProxy:
    def test_xff_with_one_proxy(self):
        """XFF: <some-ip>, <connecting-ip-seen-by-ALB> — with 1 trusted proxy,
        use ips[-1] = the IP that connected to the ALB."""
        req = _make_request("1.2.3.4, 54.200.100.1")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 1
            ip = _get_real_ip(req)
        assert ip == "54.200.100.1"

    def test_xff_single_ip_fallback(self):
        """Only 1 IP in XFF with 1 trusted proxy — not enough to strip, use last."""
        req = _make_request("1.2.3.4")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 1
            ip = _get_real_ip(req)
        assert ip == "1.2.3.4"

    def test_no_xff_uses_client_host(self):
        req = _make_request(None, client_host="5.6.7.8")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 1
            ip = _get_real_ip(req)
        assert ip == "5.6.7.8"


# ── _get_real_ip — two proxies / CloudFront + ALB (TRUSTED_PROXY_COUNT=2) ─────

class TestGetRealIpTwoProxies:
    def test_cloudfront_alb_chain(self):
        """XFF: <client>, <cloudfront-ip> — 2 trusted proxies → ips[0] = client."""
        req = _make_request("1.2.3.4, 13.225.100.50")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 2
            ip = _get_real_ip(req)
        assert ip == "1.2.3.4"

    def test_three_hops(self):
        """XFF: <forged-or-extra-proxy>, <real-client>, <cf-ip> with 2 trusted.
        ips[-2] strips the last 2 trusted entries and returns the leftmost
        remaining IP — the outermost non-trusted address seen by CF."""
        req = _make_request("9.8.7.6, 13.0.0.1, 52.0.0.1")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 2
            ip = _get_real_ip(req)
        assert ip == "13.0.0.1"  # ips[-2]: IP that CF saw as connecting client

    def test_bypass_cloudfront_short_chain_fallback(self):
        """
        Attacker bypasses CloudFront, hits ALB directly with no XFF.
        ALB adds attacker IP → XFF: <attacker>.
        With 2 trusted proxies, len(ips)=1 ≤ 2 → fall through to last IP.
        """
        req = _make_request("5.6.7.8")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 2
            ip = _get_real_ip(req)
        assert ip == "5.6.7.8"

    def test_private_candidate_falls_back_to_last(self):
        """If the computed candidate IP is private, fall back to last XFF entry."""
        req = _make_request("192.168.1.1, 13.0.0.1")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 2
            ip = _get_real_ip(req)
        # candidate = 192.168.1.1 (private) → skip → last = 13.0.0.1
        assert ip == "13.0.0.1"


# ── _get_real_ip — edge cases ─────────────────────────────────────────────────

class TestGetRealIpEdgeCases:
    def test_empty_xff(self):
        req = _make_request("", client_host="3.3.3.3")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 1
            ip = _get_real_ip(req)
        assert ip == "3.3.3.3"

    def test_whitespace_xff(self):
        """Whitespace around IPs is stripped; last IP is selected with N=1."""
        req = _make_request("  1.2.3.4  ,  5.6.7.8  ")
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 1
            ip = _get_real_ip(req)
        assert ip == "5.6.7.8"

    def test_no_client_no_xff_returns_unknown(self):
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "client": None,
        }
        req = Request(scope)
        with patch("app.core.limiter.settings") as mock_settings:
            mock_settings.TRUSTED_PROXY_COUNT = 1
            ip = _get_real_ip(req)
        assert ip == "unknown"
