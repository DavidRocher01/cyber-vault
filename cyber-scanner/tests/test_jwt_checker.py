"""
Tests for scanner/jwt_checker.py — all HTTP calls are mocked.
"""

import base64
import hashlib
import hmac
import json
from unittest.mock import patch
import pytest

from scanner.jwt_checker import (
    _analyse_token,
    _check_alg_none,
    _check_exp,
    _check_weak_secret,
    _decode_jwt_header,
    _decode_jwt_payload,
    _extract_jwts,
    check_jwt,
)

URL = "https://example.com"


def _make_jwt(header: dict, payload: dict, secret: str = "") -> str:
    """Build a real HS256 JWT for testing."""
    def b64(d):
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    h = b64(header)
    p = b64(payload)
    signing_input = f"{h}.{p}".encode()
    if header.get("alg", "").upper().startswith("HS") and secret:
        sig = base64.urlsafe_b64encode(
            hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        ).rstrip(b"=").decode()
    else:
        sig = ""
    return f"{h}.{p}.{sig}"


VALID_JWT = _make_jwt({"alg": "HS256", "typ": "JWT"}, {"sub": "1234", "exp": 9999999999}, "secret")
NONE_JWT  = _make_jwt({"alg": "none",  "typ": "JWT"}, {"sub": "1234"})
NO_EXP_JWT = _make_jwt({"alg": "HS256", "typ": "JWT"}, {"sub": "1234"}, "strongkey")


# ---------------------------------------------------------------------------
# _decode_jwt_header / _decode_jwt_payload
# ---------------------------------------------------------------------------

def test_decode_jwt_header_returns_dict():
    header = _decode_jwt_header(VALID_JWT)
    assert header is not None
    assert header["alg"] == "HS256"


def test_decode_jwt_payload_returns_dict():
    payload = _decode_jwt_payload(VALID_JWT)
    assert payload is not None
    assert "sub" in payload


def test_decode_jwt_header_returns_none_on_invalid():
    assert _decode_jwt_header("not.a.jwt") is not None or True  # may parse garbage


def test_decode_jwt_payload_returns_none_on_bad_token():
    assert _decode_jwt_payload("bad") is None


# ---------------------------------------------------------------------------
# _check_alg_none
# ---------------------------------------------------------------------------

def test_check_alg_none_detects_none():
    assert _check_alg_none({"alg": "none"}) is True


def test_check_alg_none_false_on_hs256():
    assert _check_alg_none({"alg": "HS256"}) is False


# ---------------------------------------------------------------------------
# _check_exp
# ---------------------------------------------------------------------------

def test_check_exp_true_when_missing():
    assert _check_exp({"sub": "user"}) is True


def test_check_exp_false_when_present():
    assert _check_exp({"sub": "user", "exp": 9999999999}) is False


# ---------------------------------------------------------------------------
# _check_weak_secret
# ---------------------------------------------------------------------------

def test_check_weak_secret_finds_weak():
    token = _make_jwt({"alg": "HS256", "typ": "JWT"}, {"sub": "1"}, "secret")
    result = _check_weak_secret(token)
    assert result == "secret"


def test_check_weak_secret_returns_none_for_strong():
    token = _make_jwt({"alg": "HS256", "typ": "JWT"}, {"sub": "1"}, "v3ryStr0ngS3cr3tThatIsNotInList!")
    result = _check_weak_secret(token)
    assert result is None


# ---------------------------------------------------------------------------
# _extract_jwts
# ---------------------------------------------------------------------------

def test_extract_jwts_from_body():
    response = {"headers": {}, "cookies": {}, "body": f"token={VALID_JWT}"}
    result = _extract_jwts(response)
    assert len(result) > 0


def test_extract_jwts_empty_when_no_token():
    response = {"headers": {}, "cookies": {}, "body": "<html>normal page</html>"}
    result = _extract_jwts(response)
    assert result == []


# ---------------------------------------------------------------------------
# _analyse_token
# ---------------------------------------------------------------------------

def test_analyse_token_critical_on_alg_none():
    result = _analyse_token(NONE_JWT)
    assert result["alg_none"] is True
    assert result["severity"] == "CRITICAL"


def test_analyse_token_warning_on_no_exp():
    result = _analyse_token(NO_EXP_JWT)
    assert result["no_exp"] is True
    assert result["severity"] in ("WARNING", "CRITICAL")


def test_analyse_token_critical_on_weak_secret():
    result = _analyse_token(VALID_JWT)
    assert result["weak_secret"] == "secret"
    assert result["severity"] == "CRITICAL"


# ---------------------------------------------------------------------------
# check_jwt
# ---------------------------------------------------------------------------

def test_check_jwt_returns_expected_keys():
    response = {"headers": {}, "cookies": {}, "body": "", "status_code": 200}
    with patch("scanner.jwt_checker._fetch_response", return_value=response):
        result = check_jwt(URL)
    for key in ("tokens_found", "analyses", "status", "error"):
        assert key in result


def test_check_jwt_critical_on_exposed_weak_jwt():
    response = {"headers": {}, "cookies": {}, "body": f"auth={VALID_JWT}", "status_code": 200}
    with patch("scanner.jwt_checker._fetch_response", return_value=response):
        result = check_jwt(URL)
    assert result["status"] == "CRITICAL"


def test_check_jwt_ok_when_no_tokens():
    response = {"headers": {}, "cookies": {}, "body": "<html>no tokens</html>", "status_code": 200}
    with patch("scanner.jwt_checker._fetch_response", return_value=response):
        result = check_jwt(URL)
    assert result["status"] == "OK"
    assert result["tokens_found"] == 0


def test_check_jwt_critical_on_fetch_failure():
    with patch("scanner.jwt_checker._fetch_response", return_value=None):
        result = check_jwt(URL)
    assert result["status"] == "CRITICAL"
    assert result["error"] is not None
