"""
Tests for scanner.headers_checker.check_headers()
All network calls are mocked — no real connections are made.
"""

from unittest.mock import patch, MagicMock

import pytest
import requests

from scanner.headers_checker import check_headers
from scanner.constants import SECURITY_HEADERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, headers: dict | None = None) -> MagicMock:
    """Build a fake requests.Response-like object."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = headers or {}
    return response


# ---------------------------------------------------------------------------
# Tests — return shape
# ---------------------------------------------------------------------------

class TestCheckHeadersReturnShape:
    def test_returns_expected_keys_on_success(self):
        mock_resp = _mock_response(200, {})
        with patch("requests.get", return_value=mock_resp):
            result = check_headers("https://example.com")

        expected_keys = {"status_code", "headers_found", "headers_missing", "score", "status", "error"}
        assert set(result.keys()) == expected_keys

    def test_returns_expected_keys_on_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            result = check_headers("https://nonexistent.invalid")

        expected_keys = {"status_code", "headers_found", "headers_missing", "score", "status", "error"}
        assert set(result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Tests — error path
# ---------------------------------------------------------------------------

class TestCheckHeadersErrorPath:
    def test_connection_error_sets_error_key(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError("refused")):
            result = check_headers("https://nonexistent.invalid")

        assert result["error"] is not None
        assert "Connection" in result["error"]
        assert result["status"] == "CRITICAL"

    def test_timeout_sets_error_key(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout()):
            result = check_headers("https://example.com")

        assert result["error"] is not None
        assert result["status"] == "CRITICAL"

    def test_too_many_redirects_sets_error_key(self):
        with patch("requests.get", side_effect=requests.exceptions.TooManyRedirects()):
            result = check_headers("https://example.com")

        assert result["error"] is not None
        assert result["status"] == "CRITICAL"


# ---------------------------------------------------------------------------
# Tests — scoring logic
# ---------------------------------------------------------------------------

class TestCheckHeadersScoreLogic:
    def test_no_headers_present_score_zero_status_critical(self):
        mock_resp = _mock_response(200, {})
        with patch("requests.get", return_value=mock_resp):
            result = check_headers("https://example.com")

        assert result["score"] == 0
        assert result["status"] == "CRITICAL"
        assert len(result["headers_missing"]) == len(SECURITY_HEADERS)
        assert result["headers_found"] == []

    def test_all_headers_present_score_six_status_ok(self):
        all_headers = {h: "value" for h in SECURITY_HEADERS}
        mock_resp = _mock_response(200, all_headers)
        with patch("requests.get", return_value=mock_resp):
            result = check_headers("https://example.com")

        assert result["score"] == 6
        assert result["status"] == "OK"
        assert result["headers_missing"] == []
        assert len(result["headers_found"]) == 6

    def test_four_headers_present_status_warning(self):
        partial_headers = {h: "value" for h in SECURITY_HEADERS[:4]}
        mock_resp = _mock_response(200, partial_headers)
        with patch("requests.get", return_value=mock_resp):
            result = check_headers("https://example.com")

        assert result["score"] == 4
        assert result["status"] == "WARNING"

    def test_header_check_is_case_insensitive(self):
        # Headers returned in uppercase should still be detected
        uppercased = {h.upper(): "value" for h in SECURITY_HEADERS}
        mock_resp = _mock_response(200, uppercased)
        with patch("requests.get", return_value=mock_resp):
            result = check_headers("https://example.com")

        assert result["score"] == 6
        assert result["status"] == "OK"

    def test_status_code_is_recorded(self):
        mock_resp = _mock_response(403, {})
        with patch("requests.get", return_value=mock_resp):
            result = check_headers("https://example.com")

        assert result["status_code"] == 403
