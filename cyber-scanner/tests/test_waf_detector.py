"""
Tests for scanner/waf_detector.py — all HTTP calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests as req_lib

from scanner.waf_detector import (
    _detect_from_response,
    _probe,
    detect_waf,
)

URL = "https://example.com"


def _make_probe(headers: dict = None, cookies: list = None, status_code: int = 200):
    return {
        "headers": headers or {},
        "cookies": cookies or [],
        "status_code": status_code,
    }


# ---------------------------------------------------------------------------
# _probe
# ---------------------------------------------------------------------------

def test_probe_returns_dict_on_success():
    mock_resp = MagicMock()
    mock_resp.headers = {"server": "nginx"}
    mock_resp.cookies = []
    mock_resp.status_code = 200
    with patch("scanner.waf_detector.requests.get", return_value=mock_resp):
        result = _probe(URL)
    assert result is not None
    assert result["status_code"] == 200


def test_probe_returns_none_on_connection_error():
    with patch("scanner.waf_detector.requests.get", side_effect=req_lib.exceptions.ConnectionError):
        result = _probe(URL)
    assert result is None


# ---------------------------------------------------------------------------
# _detect_from_response
# ---------------------------------------------------------------------------

def test_detect_cloudflare_from_cf_ray_header():
    probe = _make_probe(headers={"cf-ray": "abc123-CDG"})
    assert _detect_from_response(probe) == "Cloudflare"


def test_detect_sucuri_from_header():
    probe = _make_probe(headers={"x-sucuri-id": "123456"})
    assert _detect_from_response(probe) == "Sucuri"


def test_detect_imperva_from_cookie():
    probe = _make_probe(cookies=["incap_ses_123"])
    assert _detect_from_response(probe) == "Imperva Incapsula"


def test_detect_returns_none_for_clean_response():
    probe = _make_probe(headers={"server": "nginx"}, cookies=[])
    assert _detect_from_response(probe) is None


# ---------------------------------------------------------------------------
# detect_waf
# ---------------------------------------------------------------------------

def test_detect_waf_cloudflare_via_header():
    normal = _make_probe(headers={"cf-ray": "abc123"})
    with patch("scanner.waf_detector._probe", return_value=normal):
        result = detect_waf(URL)
    assert result["detected"] is True
    assert result["waf_name"] == "Cloudflare"
    assert result["method"] == "header_signature"
    assert result["status"] == "WARNING"


def test_detect_waf_detected_via_payload_block():
    clean = _make_probe(headers={"server": "nginx"})
    blocked = _make_probe(headers={}, status_code=403)
    calls = [clean, blocked]
    with patch("scanner.waf_detector._probe", side_effect=calls):
        result = detect_waf(URL)
    assert result["detected"] is True
    assert result["method"] == "payload_block"
    assert result["block_status"] == 403


def test_detect_waf_not_detected():
    clean = _make_probe(headers={"server": "nginx"})
    no_block = _make_probe(headers={}, status_code=200)
    with patch("scanner.waf_detector._probe", side_effect=[clean, no_block]):
        result = detect_waf(URL)
    assert result["detected"] is False
    assert result["status"] == "OK"


def test_detect_waf_critical_on_connection_error():
    with patch("scanner.waf_detector._probe", return_value=None):
        result = detect_waf(URL)
    assert result["error"] is not None


def test_detect_waf_returns_expected_keys():
    clean = _make_probe()
    no_block = _make_probe(status_code=200)
    with patch("scanner.waf_detector._probe", side_effect=[clean, no_block]):
        result = detect_waf(URL)
    for key in ("detected", "waf_name", "method", "block_status", "status", "error"):
        assert key in result
