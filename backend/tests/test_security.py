"""
Unit tests — app.core.security
Covers: hash_password, verify_password, create_access_token,
        decode_access_token, create_refresh_token
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
