"""
Module H4 — Robots.txt & Sitemap Analyser (Tier 4)
Parses robots.txt for disallowed paths (potential hidden endpoints)
and sitemap.xml for exposed URL structure.
No API key required.
"""

import re
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

REQUEST_TIMEOUT = 8

# Patterns that suggest sensitive disallowed paths
SENSITIVE_PATTERNS = [
    r"/admin",
    r"/backup",
    r"/config",
    r"/private",
    r"/secret",
    r"/internal",
    r"/api",
    r"/db",
    r"/database",
    r"/test",
    r"/staging",
    r"/dev",
    r"\.sql",
    r"\.env",
    r"\.bak",
    r"/phpmyadmin",
    r"/wp-admin",
]


def _fetch(url: str) -> str | None:
    """Fetch URL content, return text or None."""
    try:
        resp = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
            verify=False,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            return resp.text[:50_000]
        return None
    except requests.exceptions.RequestException:
        return None


def _parse_robots(content: str) -> dict[str, Any]:
    """
    Parse robots.txt content.
    Returns disallowed paths, allowed paths, and sitemaps declared.
    """
    disallowed: list[str] = []
    allowed: list[str]    = []
    sitemaps: list[str]   = []

    for line in content.splitlines():
        line = line.strip()
        if line.lower().startswith("disallow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                disallowed.append(path)
        elif line.lower().startswith("allow:"):
            path = line.split(":", 1)[1].strip()
            if path:
                allowed.append(path)
        elif line.lower().startswith("sitemap:"):
            url = line.split(":", 1)[1].strip()
            if url:
                sitemaps.append(url)

    return {"disallowed": disallowed, "allowed": allowed, "sitemaps": sitemaps}


def _find_sensitive_paths(paths: list[str]) -> list[str]:
    """Return paths that match known sensitive patterns."""
    sensitive = []
    for path in paths:
        if any(re.search(p, path, re.IGNORECASE) for p in SENSITIVE_PATTERNS):
            sensitive.append(path)
    return sensitive


def _parse_sitemap(content: str) -> list[str]:
    """Extract URLs from sitemap XML content."""
    return re.findall(r"<loc>\s*(https?://[^<]+)\s*</loc>", content, re.IGNORECASE)


def analyse_robots_sitemap(url: str) -> dict[str, Any]:
    """
    Analyse robots.txt and sitemap.xml for information disclosure.

    Args:
        url: Base URL (e.g. "https://example.com")

    Returns:
        A dict with keys:
            robots_found        — True if robots.txt exists
            disallowed_paths    — all Disallow entries
            sensitive_disallowed— disallowed paths matching sensitive patterns
            sitemaps_declared   — sitemap URLs declared in robots.txt
            sitemap_found       — True if sitemap.xml accessible
            sitemap_url_count   — number of URLs in sitemap
            sitemap_urls        — first 20 sitemap URLs
            status              — "OK" | "WARNING" | "CRITICAL"
            error               — error message or None
    """
    result: dict[str, Any] = {
        "robots_found":          False,
        "disallowed_paths":      [],
        "sensitive_disallowed":  [],
        "sitemaps_declared":     [],
        "sitemap_found":         False,
        "sitemap_url_count":     0,
        "sitemap_urls":          [],
        "status":                "OK",
        "error":                 None,
    }

    base = url.rstrip("/")

    # --- robots.txt ---
    robots_content = _fetch(f"{base}/robots.txt")
    if robots_content:
        result["robots_found"] = True
        parsed = _parse_robots(robots_content)
        result["disallowed_paths"]   = parsed["disallowed"]
        result["sitemaps_declared"]  = parsed["sitemaps"]
        result["sensitive_disallowed"] = _find_sensitive_paths(parsed["disallowed"])

    # --- sitemap.xml ---
    sitemap_url = result["sitemaps_declared"][0] if result["sitemaps_declared"] else f"{base}/sitemap.xml"
    sitemap_content = _fetch(sitemap_url)
    if sitemap_content:
        urls = _parse_sitemap(sitemap_content)
        result["sitemap_found"]     = True
        result["sitemap_url_count"] = len(urls)
        result["sitemap_urls"]      = urls[:20]

    # --- Determine status ---
    if result["sensitive_disallowed"]:
        result["status"] = "WARNING"
    # If robots.txt discloses many paths, it's an info leak
    if len(result["disallowed_paths"]) > 10:
        result["status"] = "WARNING"

    return result
