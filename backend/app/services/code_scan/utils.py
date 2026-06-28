"""
utils.py — URL sanitisation helpers for the code scan service.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse


def _sanitize_repo_url(url: str, token: str | None) -> str:
    """Inject a PAT token into https:// URLs if provided."""
    if not token:
        return url
    parsed = urlparse(url)
    if parsed.scheme in ("http", "https"):
        return parsed._replace(netloc=f"{token}@{parsed.netloc}").geturl()
    return url


def _redact_url(text: str) -> str:
    """Strip embedded credentials from URLs in text to prevent token leakage."""
    return re.sub(r"https?://[^@\s/]+@", "https://", text)


def _extract_repo_name(url: str) -> str:
    """Extract owner/repo from a GitHub URL."""
    url = url.rstrip("/").rstrip(".git")
    parts = url.split("/")
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return parts[-1]
