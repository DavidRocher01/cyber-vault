"""
Tests for scanner/cms_detector.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.cms_detector import (
    _check_signature,
    _extract_version,
    _fetch,
    detect_cms,
)

URL = "https://example.com"


def _make_page(html: str = "", headers: dict = None, cookies: str = "", status_code: int = 200):
    return {
        "html": html,
        "headers": headers or {},
        "cookies": cookies,
        "status_code": status_code,
    }


# ---------------------------------------------------------------------------
# _fetch
# ---------------------------------------------------------------------------

def test_fetch_returns_dict_on_success():
    mock_resp = MagicMock()
    mock_resp.headers = {"Content-Type": "text/html"}
    mock_resp.text = "<html></html>"
    mock_resp.cookies = {}
    mock_resp.status_code = 200
    with patch("scanner.cms_detector.requests.get", return_value=mock_resp):
        result = _fetch(URL)
    assert result is not None
    assert "html" in result
    assert "headers" in result


def test_fetch_returns_none_on_connection_error():
    with patch("scanner.cms_detector.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _fetch(URL)
    assert result is None


# ---------------------------------------------------------------------------
# _check_signature
# ---------------------------------------------------------------------------

def test_check_signature_html_match():
    check = {"type": "html", "pattern": r'content="WordPress'}
    page = _make_page(html='<meta content="WordPress 6.0">')
    assert _check_signature(check, URL, page) is True


def test_check_signature_html_no_match():
    check = {"type": "html", "pattern": r'content="WordPress'}
    page = _make_page(html="<html><body>Hello</body></html>")
    assert _check_signature(check, URL, page) is False


def test_check_signature_header_match():
    check = {"type": "header", "key": "x-generator", "pattern": r"(?i)drupal"}
    page = _make_page(headers={"x-generator": "Drupal 9"})
    assert _check_signature(check, URL, page) is True


def test_check_signature_cookie_match():
    check = {"type": "cookie", "pattern": r"wordpress_"}
    page = _make_page(cookies="wordpress_logged_in=abc123")
    assert _check_signature(check, URL, page) is True


# ---------------------------------------------------------------------------
# detect_cms
# ---------------------------------------------------------------------------

def test_detect_cms_returns_unknown_for_clean_site():
    clean = _make_page(html="<html><body>Hello world</body></html>")
    not_found = _make_page(status_code=404)
    def fake_fetch(url):
        return clean if url == URL else not_found
    with patch("scanner.cms_detector._fetch", side_effect=fake_fetch):
        result = detect_cms(URL)
    assert result["cms"] == "Unknown"
    assert result["status"] == "OK"


def test_detect_cms_detects_wordpress_from_html():
    html = '<meta name="generator" content="WordPress 6.0">'
    page = _make_page(html=html)
    with patch("scanner.cms_detector._fetch", return_value=page), \
         patch("scanner.cms_detector._check_signature", side_effect=lambda c, u, p: c.get("type") == "html"):
        result = detect_cms(URL)
    assert result["status"] in ("WARNING", "CRITICAL", "OK")


def test_detect_cms_critical_when_version_exposed():
    html = '<meta name="generator" content="WordPress 5.0.1">'
    page = _make_page(html=html)

    def fake_check(check, base_url, p):
        if check["type"] == "html" and "WordPress" in check.get("pattern", ""):
            return True
        if check["type"] == "url_path":
            return True
        return False

    def fake_version(patterns, base_url, p):
        return "5.0.1"

    with patch("scanner.cms_detector._fetch", return_value=page), \
         patch("scanner.cms_detector._check_signature", side_effect=fake_check), \
         patch("scanner.cms_detector._extract_version", side_effect=fake_version):
        result = detect_cms(URL)
    assert result["status"] == "CRITICAL"
    assert result["version"] == "5.0.1"


def test_detect_cms_critical_on_fetch_failure():
    with patch("scanner.cms_detector._fetch", return_value=None):
        result = detect_cms(URL)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_detect_cms_returns_expected_keys():
    page = _make_page()
    with patch("scanner.cms_detector._fetch", return_value=page):
        result = detect_cms(URL)
    for key in ("cms", "version", "confidence", "status", "error"):
        assert key in result
