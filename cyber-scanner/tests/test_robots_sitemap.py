"""
Tests for scanner/robots_sitemap.py — all HTTP calls are mocked.
"""

from unittest.mock import patch
import pytest

from scanner.robots_sitemap import (
    _fetch,
    _find_sensitive_paths,
    _parse_robots,
    _parse_sitemap,
    analyse_robots_sitemap,
)

URL = "https://example.com"

ROBOTS_CONTENT = """
User-agent: *
Disallow: /admin/
Disallow: /backup/
Disallow: /private/
Allow: /public/
Sitemap: https://example.com/sitemap.xml
"""

SITEMAP_CONTENT = """<?xml version="1.0"?>
<urlset>
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/contact</loc></url>
</urlset>"""


# ---------------------------------------------------------------------------
# _fetch
# ---------------------------------------------------------------------------

def test_fetch_returns_content_on_200():
    mock_resp = type("R", (), {"status_code": 200, "text": "User-agent: *\nDisallow: /admin/"})()
    with patch("scanner.robots_sitemap.requests.get", return_value=mock_resp):
        result = _fetch(URL)
    assert result is not None
    assert "Disallow" in result


def test_fetch_returns_none_on_404():
    mock_resp = type("R", (), {"status_code": 404, "text": ""})()
    with patch("scanner.robots_sitemap.requests.get", return_value=mock_resp):
        result = _fetch(URL)
    assert result is None


# ---------------------------------------------------------------------------
# _parse_robots
# ---------------------------------------------------------------------------

def test_parse_robots_extracts_disallowed():
    parsed = _parse_robots(ROBOTS_CONTENT)
    assert "/admin/" in parsed["disallowed"]
    assert "/backup/" in parsed["disallowed"]


def test_parse_robots_extracts_sitemap():
    parsed = _parse_robots(ROBOTS_CONTENT)
    assert "https://example.com/sitemap.xml" in parsed["sitemaps"]


def test_parse_robots_extracts_allowed():
    parsed = _parse_robots(ROBOTS_CONTENT)
    assert "/public/" in parsed["allowed"]


def test_parse_robots_empty_content():
    parsed = _parse_robots("")
    assert parsed["disallowed"] == []
    assert parsed["sitemaps"] == []


# ---------------------------------------------------------------------------
# _find_sensitive_paths
# ---------------------------------------------------------------------------

def test_find_sensitive_paths_detects_admin():
    result = _find_sensitive_paths(["/admin/", "/about/", "/contact/"])
    assert "/admin/" in result
    assert "/about/" not in result


def test_find_sensitive_paths_detects_backup_and_config():
    result = _find_sensitive_paths(["/backup/", "/config.php", "/public/"])
    assert "/backup/" in result
    assert "/config.php" in result
    assert "/public/" not in result


# ---------------------------------------------------------------------------
# _parse_sitemap
# ---------------------------------------------------------------------------

def test_parse_sitemap_extracts_urls():
    urls = _parse_sitemap(SITEMAP_CONTENT)
    assert "https://example.com/" in urls
    assert "https://example.com/about" in urls
    assert len(urls) == 3


def test_parse_sitemap_returns_empty_on_no_loc():
    urls = _parse_sitemap("<urlset></urlset>")
    assert urls == []


# ---------------------------------------------------------------------------
# analyse_robots_sitemap
# ---------------------------------------------------------------------------

def test_analyse_robots_sitemap_returns_expected_keys():
    with patch("scanner.robots_sitemap._fetch", return_value=None):
        result = analyse_robots_sitemap(URL)
    for key in ("robots_found", "disallowed_paths", "sensitive_disallowed",
                "sitemaps_declared", "sitemap_found", "sitemap_url_count", "sitemap_urls", "status", "error"):
        assert key in result


def test_analyse_robots_sitemap_warning_on_sensitive_paths():
    def fake_fetch(url):
        if "robots" in url:
            return ROBOTS_CONTENT
        if "sitemap" in url:
            return SITEMAP_CONTENT
        return None
    with patch("scanner.robots_sitemap._fetch", side_effect=fake_fetch):
        result = analyse_robots_sitemap(URL)
    assert result["robots_found"] is True
    assert result["status"] == "WARNING"
    assert len(result["sensitive_disallowed"]) > 0


def test_analyse_robots_sitemap_ok_when_no_robots():
    with patch("scanner.robots_sitemap._fetch", return_value=None):
        result = analyse_robots_sitemap(URL)
    assert result["robots_found"] is False
    assert result["status"] == "OK"


def test_analyse_robots_sitemap_detects_sitemap_urls():
    def fake_fetch(url):
        if "sitemap" in url:
            return SITEMAP_CONTENT
        return None
    with patch("scanner.robots_sitemap._fetch", side_effect=fake_fetch):
        result = analyse_robots_sitemap(URL)
    assert result["sitemap_found"] is True
    assert result["sitemap_url_count"] == 3
