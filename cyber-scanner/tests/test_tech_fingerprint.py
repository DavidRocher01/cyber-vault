"""
Tests for scanner/tech_fingerprint.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.tech_fingerprint import (
    _fetch,
    _match_signature,
    _group_by_category,
    fingerprint_tech,
)

URL = "https://example.com"


def _make_page(html: str = "", headers: dict = None, cookies: str = ""):
    return {
        "html":    html,
        "headers": headers or {},
        "cookies": cookies,
    }


# ---------------------------------------------------------------------------
# _fetch
# ---------------------------------------------------------------------------

def test_fetch_returns_dict_on_success():
    mock_resp = MagicMock()
    mock_resp.headers = {"Server": "nginx"}
    mock_resp.text = "<html></html>"
    mock_resp.cookies = {}
    mock_resp.status_code = 200
    with patch("scanner.tech_fingerprint.requests.get", return_value=mock_resp):
        result = _fetch(URL)
    assert result is not None
    assert "html" in result
    assert "headers" in result
    assert "cookies" in result


def test_fetch_returns_none_on_connection_error():
    with patch("scanner.tech_fingerprint.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _fetch(URL)
    assert result is None


# ---------------------------------------------------------------------------
# _match_signature
# ---------------------------------------------------------------------------

def test_match_signature_html_match():
    sig = {"type": "html", "pattern": r"react\.js", "category": "js", "name": "React"}
    page = _make_page(html='<script src="react.js"></script>')
    assert _match_signature(sig, page) is True


def test_match_signature_html_no_match():
    sig = {"type": "html", "pattern": r"react\.js", "category": "js", "name": "React"}
    page = _make_page(html="<html><body>Hello</body></html>")
    assert _match_signature(sig, page) is False


def test_match_signature_header_match():
    sig = {"type": "header", "key": "server", "pattern": r"(?i)nginx", "category": "server", "name": "nginx"}
    page = _make_page(headers={"server": "nginx/1.24.0"})
    assert _match_signature(sig, page) is True


def test_match_signature_header_absent_returns_false():
    sig = {"type": "header", "key": "x-powered-by", "pattern": r"(?i)php", "category": "framework", "name": "PHP"}
    page = _make_page(headers={})
    assert _match_signature(sig, page) is False


def test_match_signature_cookie_match():
    sig = {"type": "cookie", "pattern": r"laravel_session", "category": "framework", "name": "Laravel"}
    page = _make_page(cookies="laravel_session=abc123")
    assert _match_signature(sig, page) is True


def test_match_signature_cookie_no_match():
    sig = {"type": "cookie", "pattern": r"laravel_session", "category": "framework", "name": "Laravel"}
    page = _make_page(cookies="session=xyz")
    assert _match_signature(sig, page) is False


# ---------------------------------------------------------------------------
# _group_by_category
# ---------------------------------------------------------------------------

def test_group_by_category_groups_correctly():
    matches = [
        {"category": "js",     "name": "React"},
        {"category": "js",     "name": "jQuery"},
        {"category": "server", "name": "nginx"},
    ]
    grouped = _group_by_category(matches)
    assert "js" in grouped
    assert "React" in grouped["js"]
    assert "jQuery" in grouped["js"]
    assert grouped["server"] == ["nginx"]


def test_group_by_category_deduplicates():
    matches = [
        {"category": "js", "name": "React"},
        {"category": "js", "name": "React"},
    ]
    grouped = _group_by_category(matches)
    assert grouped["js"].count("React") == 1


# ---------------------------------------------------------------------------
# fingerprint_tech
# ---------------------------------------------------------------------------

def test_fingerprint_tech_returns_expected_keys():
    page = _make_page()
    with patch("scanner.tech_fingerprint._fetch", return_value=page):
        result = fingerprint_tech(URL)
    for key in ("technologies", "total", "status", "error"):
        assert key in result


def test_fingerprint_tech_detects_react():
    page = _make_page(html='<div data-reactroot=""><script src="react.min.js"></script></div>')
    with patch("scanner.tech_fingerprint._fetch", return_value=page):
        result = fingerprint_tech(URL)
    assert result["total"] > 0
    assert "React" in result["technologies"].get("js", [])


def test_fingerprint_tech_warning_on_version_disclosure():
    page = _make_page(headers={"server": "Apache/2.4.51", "x-powered-by": ""})
    with patch("scanner.tech_fingerprint._fetch", return_value=page):
        result = fingerprint_tech(URL)
    assert result["status"] == "WARNING"
    assert result["error"] is not None


def test_fingerprint_tech_critical_on_fetch_failure():
    with patch("scanner.tech_fingerprint._fetch", return_value=None):
        result = fingerprint_tech(URL)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None


def test_fingerprint_tech_ok_on_clean_site():
    page = _make_page(html="<html><body>Hello</body></html>", headers={"server": "cloudflare"})
    with patch("scanner.tech_fingerprint._fetch", return_value=page):
        result = fingerprint_tech(URL)
    assert result["status"] in ("OK", "WARNING")
