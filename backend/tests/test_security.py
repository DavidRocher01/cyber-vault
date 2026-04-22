"""
Unit tests — app.core.security
Covers: hash_password, verify_password, create_access_token,
        decode_access_token, create_refresh_token, hash_token,
        make_unsubscribe_token
"""

import time
import pytest
from jose import jwt

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    hash_password,
    hash_token,
    make_unsubscribe_token,
    verify_password,
)


# ── hash_password / verify_password ─────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("secret")
        assert hashed != "secret"

    def test_correct_password_verifies(self):
        hashed = hash_password("MyPass123!")
        assert verify_password("MyPass123!", hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("MyPass123!")
        assert verify_password("wrong", hashed) is False

    def test_empty_password_hashes(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses random salt — hashes must differ."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2

    def test_unicode_password(self):
        hashed = hash_password("pässwörD€123")
        assert verify_password("pässwörD€123", hashed) is True


# ── create_access_token / decode_access_token ────────────────────────────────

class TestAccessToken:
    def test_token_is_string(self):
        token = create_access_token("user@test.com")
        assert isinstance(token, str)

    def test_decode_returns_subject(self):
        token = create_access_token("user@test.com")
        sub = decode_access_token(token)
        assert sub == "user@test.com"

    def test_invalid_token_returns_none(self):
        assert decode_access_token("not.a.valid.token") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("user@test.com")
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None

    def test_wrong_secret_returns_none(self):
        payload = {"sub": "user@test.com", "exp": int(time.time()) + 3600}
        bad_token = jwt.encode(payload, "wrong-secret", algorithm=settings.ALGORITHM)
        assert decode_access_token(bad_token) is None

    def test_expired_token_returns_none(self):
        payload = {"sub": "user@test.com", "exp": int(time.time()) - 1}
        expired = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        assert decode_access_token(expired) is None

    def test_different_subjects_produce_different_tokens(self):
        t1 = create_access_token("a@test.com")
        t2 = create_access_token("b@test.com")
        assert t1 != t2


# ── hash_token (HMAC-SHA256) ──────────────────────────────────────────────────

class TestHashToken:
    def test_output_is_64_hex_chars(self):
        h = hash_token("any-raw-token")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_token_same_hash(self):
        assert hash_token("tok") == hash_token("tok")

    def test_different_tokens_different_hashes(self):
        assert hash_token("token-a") != hash_token("token-b")

    def test_raw_token_not_in_hash(self):
        raw = "supersecret123"
        assert raw not in hash_token(raw)

    def test_hash_changes_with_secret_key(self):
        """HMAC-SHA256 output depends on the key — changing the key changes the hash."""
        from unittest.mock import patch
        h1 = hash_token("same-token")
        with patch("app.core.security.settings") as mock_settings:
            mock_settings.SECRET_KEY = "different-secret"
            h2 = hash_token("same-token")
        assert h1 != h2

    def test_consistent_across_calls(self):
        """hash_token must be deterministic for DB lookups to work."""
        raw = create_refresh_token()
        assert hash_token(raw) == hash_token(raw)


# ── create_refresh_token ─────────────────────────────────────────────────────

class TestRefreshToken:
    def test_token_is_string(self):
        assert isinstance(create_refresh_token(), str)

    def test_token_length_sufficient(self):
        """urlsafe_b64(64 bytes) → ~86 chars; at least 32 chars expected."""
        assert len(create_refresh_token()) >= 32

    def test_tokens_are_unique(self):
        tokens = {create_refresh_token() for _ in range(100)}
        assert len(tokens) == 100


# ── make_unsubscribe_token ───────────────────────────────────────────────────

class TestMakeUnsubscribeToken:
    def test_output_is_64_hex_chars(self):
        t = make_unsubscribe_token("user@example.com")
        assert len(t) == 64
        assert all(c in "0123456789abcdef" for c in t)

    def test_deterministic_same_email(self):
        """Same email must always produce the same token (used in newsletter URLs)."""
        assert make_unsubscribe_token("a@b.com") == make_unsubscribe_token("a@b.com")

    def test_different_emails_different_tokens(self):
        assert make_unsubscribe_token("a@b.com") != make_unsubscribe_token("c@d.com")

    def test_distinct_from_hash_token(self):
        """make_unsubscribe_token uses a namespaced message — output must differ from hash_token."""
        email = "user@example.com"
        assert make_unsubscribe_token(email) != hash_token(email)

    def test_changes_with_secret_key(self):
        from unittest.mock import patch
        t1 = make_unsubscribe_token("user@example.com")
        with patch("app.core.security.settings") as mock_settings:
            mock_settings.SECRET_KEY = "other-secret"
            t2 = make_unsubscribe_token("user@example.com")
        assert t1 != t2

    def test_email_not_in_output(self):
        email = "identifiable@example.com"
        assert email not in make_unsubscribe_token(email)
