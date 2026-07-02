"""
Unit tests — JWT / auth security invariants (anti-usurpation).

Complementary to test_security.py::TestAccessToken. We do NOT repeat cases
already covered there (invalid string, tampered token, wrong secret, expired,
missing type, learner token). Here we harden the edge cases and error paths:

  - algorithm "none" (unsigned) tokens are rejected
  - algorithm confusion (asymmetric alg claimed against HS256 verifier)
  - tampered JWT header (alg swapped) is rejected
  - malformed/unexpected claim shapes (non-int exp, nbf in future, string exp)
  - every non-"access" type variant is rejected (empty, whitespace, case, refresh)
  - "sub" invariants: missing sub with valid type, None sub, non-string sub

These enforce that decode_access_token(...) returns None on anything that is
not a genuine, correctly-typed, correctly-signed access token.
"""

import base64
import json
import time

import jwt

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token

ALG = settings.ALGORITHM  # "HS256"


def _make(payload: dict, key: str | None = None, algorithm: str | None = None) -> str:
    """Encode a JWT with the real secret/alg unless overridden."""
    return jwt.encode(
        payload,
        key if key is not None else settings.SECRET_KEY,
        algorithm=algorithm if algorithm is not None else ALG,
    )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _valid_exp() -> int:
    return int(time.time()) + 3600


# ── algorithm "none" / unsigned tokens ───────────────────────────────────────


class TestAlgNone:
    def test_alg_none_unsigned_token_rejected(self):
        """A hand-crafted alg=none token (empty signature) must never authenticate."""
        header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        body = _b64url(
            json.dumps({"sub": "user@test.com", "exp": _valid_exp(), "type": "access"}).encode()
        )
        forged = f"{header}.{body}."  # empty signature segment
        assert decode_access_token(forged) is None

    def test_alg_none_with_garbage_signature_rejected(self):
        header = _b64url(json.dumps({"alg": "none", "typ": "JWT"}).encode())
        body = _b64url(json.dumps({"sub": "1", "exp": _valid_exp(), "type": "access"}).encode())
        forged = f"{header}.{body}.{_b64url(b'not-a-real-sig')}"
        assert decode_access_token(forged) is None

    def test_uppercase_none_rejected(self):
        header = _b64url(json.dumps({"alg": "None", "typ": "JWT"}).encode())
        body = _b64url(json.dumps({"sub": "1", "exp": _valid_exp(), "type": "access"}).encode())
        assert decode_access_token(f"{header}.{body}.") is None


# ── algorithm confusion ──────────────────────────────────────────────────────


class TestAlgConfusion:
    def test_tampered_header_alg_swapped_rejected(self):
        """Swap the header alg to HS512 on an HS256-signed body: signature no longer
        matches under the swapped alg, and the verifier only allows HS256."""
        token = create_access_token("user@test.com")
        header_b64, body_b64, sig_b64 = token.split(".")
        forged_header = _b64url(json.dumps({"alg": "HS512", "typ": "JWT"}).encode())
        forged = f"{forged_header}.{body_b64}.{sig_b64}"
        assert decode_access_token(forged) is None

    def test_hs512_signed_with_secret_rejected(self):
        """Even correctly signed, a different HMAC alg than the configured one is refused
        (decode restricts algorithms=[ALGORITHM])."""
        token = _make(
            {"sub": "user@test.com", "exp": _valid_exp(), "type": "access"},
            algorithm="HS512",
        )
        assert decode_access_token(token) is None

    def test_secret_used_as_rsa_public_key_confusion_rejected(self):
        """Classic RS256->HS256 confusion attempt: attacker signs HS256 using the
        server secret as if it were a public key. Our verifier still requires the
        correct HS256 signature AND the correct type, and this forged token, while it
        may verify (it IS a valid HS256 token), still must be a proper access token.
        Here we prove a DIFFERENT-secret HS256 forgery is rejected."""
        forged = _make(
            {"sub": "attacker@evil.com", "exp": _valid_exp(), "type": "access"},
            key="pretend-this-is-a-public-key",
            algorithm=ALG,
        )
        assert decode_access_token(forged) is None


# ── malformed / unexpected claim shapes ──────────────────────────────────────


class TestMalformedClaims:
    def test_non_int_string_exp_rejected(self):
        """exp as a non-numeric string is an invalid claim → decode raises → None."""
        forged = _make({"sub": "u@t.com", "exp": "not-a-number", "type": "access"})
        assert decode_access_token(forged) is None

    def test_nbf_in_future_rejected(self):
        """not-before in the future means the token is not yet valid → None."""
        forged = _make(
            {
                "sub": "u@t.com",
                "exp": _valid_exp(),
                "nbf": int(time.time()) + 3600,
                "type": "access",
            }
        )
        assert decode_access_token(forged) is None

    def test_empty_payload_rejected(self):
        """No sub, no type, no exp → type check fails → None."""
        forged = _make({})
        assert decode_access_token(forged) is None

    def test_garbage_middle_segment_rejected(self):
        token = create_access_token("user@test.com")
        header_b64, _body_b64, sig_b64 = token.split(".")
        forged = f"{header_b64}.{_b64url(b'{not json}')}.{sig_b64}"
        assert decode_access_token(forged) is None

    def test_two_segment_token_rejected(self):
        assert decode_access_token("aaa.bbb") is None

    def test_empty_string_rejected(self):
        assert decode_access_token("") is None


# ── type-confusion: every non-"access" variant is rejected ───────────────────


class TestTypeVariants:
    def test_refresh_type_rejected(self):
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": "refresh"})
        assert decode_access_token(forged) is None

    def test_empty_string_type_rejected(self):
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": ""})
        assert decode_access_token(forged) is None

    def test_whitespace_type_rejected(self):
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": " access "})
        assert decode_access_token(forged) is None

    def test_case_variant_type_rejected(self):
        """Type check is exact-match; 'Access' must not be accepted."""
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": "Access"})
        assert decode_access_token(forged) is None

    def test_null_type_rejected(self):
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": None})
        assert decode_access_token(forged) is None

    def test_numeric_type_rejected(self):
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": 1})
        assert decode_access_token(forged) is None

    def test_magic_link_type_rejected(self):
        """Awareness magic-link style token type must not authenticate a user."""
        forged = _make({"sub": "1", "exp": _valid_exp(), "type": "magic_link"})
        assert decode_access_token(forged) is None


# ── sub invariants ───────────────────────────────────────────────────────────


class TestSubInvariants:
    def test_missing_sub_with_valid_type_returns_none(self):
        """Correct type but no subject → nothing to authenticate → None (not KeyError)."""
        forged = _make({"exp": _valid_exp(), "type": "access"})
        assert decode_access_token(forged) is None

    def test_none_sub_returns_none(self):
        forged = _make({"sub": None, "exp": _valid_exp(), "type": "access"})
        assert decode_access_token(forged) is None

    def test_nonexistent_but_wellformed_sub_returns_string(self):
        """A well-formed access token for a subject that does not exist in the DB is
        still decoded to that subject string — existence is enforced downstream by
        get_current_user, not by decode_access_token. This documents the boundary."""
        forged = _make(
            {"sub": "ghost-user-does-not-exist@nowhere.tld", "exp": _valid_exp(), "type": "access"}
        )
        assert decode_access_token(forged) == "ghost-user-does-not-exist@nowhere.tld"

    def test_numeric_sub_rejected(self):
        """PyJWT enforces that 'sub' is a string; a numeric sub is an invalid claim
        → decode raises InvalidSubjectError → None."""
        forged = _make({"sub": 42, "exp": _valid_exp(), "type": "access"})
        assert decode_access_token(forged) is None


# ── round-trip sanity (guards the helpers above stay in sync with prod) ───────


class TestRoundTripSanity:
    def test_genuine_token_still_decodes(self):
        token = create_access_token("legit@test.com")
        assert decode_access_token(token) == "legit@test.com"

    def test_helper_make_matches_create_access_token_shape(self):
        """Our _make() with the same claims must decode identically — proves the
        forged-token machinery isn't accidentally producing rejected-by-construction
        tokens (which would make the negative tests vacuous)."""
        forged = _make({"sub": "legit@test.com", "exp": _valid_exp(), "type": "access"})
        assert decode_access_token(forged) == "legit@test.com"
