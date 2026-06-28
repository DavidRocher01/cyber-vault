"""
Unit tests — phishing_service.py : domain verification helpers.

Covers:
  1. request_domain_verification — create new record, reuse verified, refresh token on re-request
  2. check_domain_verification — already-verified short-circuit
  3. check_domain_verification — dev-mode auto-approval
  4. check_domain_verification — DNS TXT match (mocked resolver)
  5. check_domain_verification — DNS TXT mismatch
  6. check_domain_verification — DNS resolution failure (NXDOMAIN / timeout)
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.phishing import PhishingDomainVerification
from app.models.user import User
from app.services import phishing_service

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_user(db: AsyncSession, email: str = "domaintest@test.com") -> User:
    user = User(email=email, hashed_password=hash_password("pass"))
    db.add(user)
    await db.flush()
    return user


async def _seed_verification(
    db: AsyncSession,
    user_id: int,
    domain: str = "acme.com",
    *,
    verified: bool = False,
    token: str = "rocher-verify-existing-token",
) -> PhishingDomainVerification:
    record = PhishingDomainVerification(
        user_id=user_id,
        domain=domain,
        verification_token=token,
        verified=verified,
        verified_at=datetime.now(UTC) if verified else None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


# ---------------------------------------------------------------------------
# 1. request_domain_verification
# ---------------------------------------------------------------------------


class TestRequestDomainVerification:
    @pytest.mark.asyncio
    async def test_creates_new_record_for_unknown_domain(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "rdv1@test.com")
        await db_session.commit()

        record = await phishing_service.request_domain_verification(
            user.id, "newdomain.com", db_session
        )

        assert record.domain == "newdomain.com"
        assert record.user_id == user.id
        assert record.verification_token.startswith("rocher-verify-")
        assert record.verified is False

    @pytest.mark.asyncio
    async def test_token_format_is_correct(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "rdv2@test.com")
        await db_session.commit()

        record = await phishing_service.request_domain_verification(
            user.id, "formatted.com", db_session
        )

        # Token must start with "rocher-verify-" and have a random suffix
        parts = record.verification_token.split("rocher-verify-")
        assert len(parts) == 2
        assert len(parts[1]) >= 16  # token_urlsafe(16) yields ≥ 21 chars

    @pytest.mark.asyncio
    async def test_returns_existing_verified_record_unchanged(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "rdv3@test.com")
        existing = await _seed_verification(
            db_session, user.id, "verified.com", verified=True, token="rocher-verify-abc123"
        )
        await db_session.commit()

        returned = await phishing_service.request_domain_verification(
            user.id, "verified.com", db_session
        )

        # Verified record must be returned as-is; token must not change
        assert returned.id == existing.id
        assert returned.verified is True
        assert returned.verification_token == "rocher-verify-abc123"

    @pytest.mark.asyncio
    async def test_refreshes_token_for_unverified_existing_record(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "rdv4@test.com")
        existing = await _seed_verification(
            db_session, user.id, "retry.com", verified=False, token="rocher-verify-old"
        )
        await db_session.commit()
        old_token = existing.verification_token

        returned = await phishing_service.request_domain_verification(
            user.id, "retry.com", db_session
        )

        # Same record but with a new token
        assert returned.id == existing.id
        assert returned.verification_token != old_token
        assert returned.verification_token.startswith("rocher-verify-")
        assert returned.verified is False

    @pytest.mark.asyncio
    async def test_different_users_get_separate_records(self, db_session: AsyncSession):
        u1 = await _seed_user(db_session, "rdv5a@test.com")
        u2 = await _seed_user(db_session, "rdv5b@test.com")
        await db_session.commit()

        r1 = await phishing_service.request_domain_verification(u1.id, "shared.com", db_session)
        r2 = await phishing_service.request_domain_verification(u2.id, "shared.com", db_session)

        assert r1.id != r2.id
        assert r1.user_id == u1.id
        assert r2.user_id == u2.id


# ---------------------------------------------------------------------------
# 2. check_domain_verification — already verified (short-circuit)
# ---------------------------------------------------------------------------


class TestCheckDomainVerificationAlreadyVerified:
    @pytest.mark.asyncio
    async def test_returns_true_immediately_when_verified(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "chk1@test.com")
        record = await _seed_verification(db_session, user.id, "done.com", verified=True)
        await db_session.commit()

        result = await phishing_service.check_domain_verification(record, db_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_does_not_call_dns_when_already_verified(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "chk2@test.com")
        record = await _seed_verification(db_session, user.id, "nodns.com", verified=True)
        await db_session.commit()

        with patch("dns.resolver.resolve") as mock_dns:
            await phishing_service.check_domain_verification(record, db_session)

        mock_dns.assert_not_called()


# ---------------------------------------------------------------------------
# 3. check_domain_verification — dev-mode auto-approval
# ---------------------------------------------------------------------------


class TestCheckDomainVerificationDevMode:
    @pytest.mark.asyncio
    async def test_dev_mode_auto_approves(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "dev1@test.com")
        record = await _seed_verification(db_session, user.id, "devdomain.com", verified=False)
        await db_session.commit()

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.APP_ENV = "development"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is True
        assert record.verified is True
        assert record.verified_at is not None

    @pytest.mark.asyncio
    async def test_dev_mode_sets_verified_at_timestamp(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "dev2@test.com")
        record = await _seed_verification(db_session, user.id, "ts.com", verified=False)
        await db_session.commit()

        with patch("app.core.config.settings") as mock_settings:
            mock_settings.APP_ENV = "development"
            await phishing_service.check_domain_verification(record, db_session)

        assert isinstance(record.verified_at, datetime)


# ---------------------------------------------------------------------------
# 4. check_domain_verification — DNS TXT match (mocked resolver)
# ---------------------------------------------------------------------------


class TestCheckDomainVerificationDnsMatch:
    def _make_dns_answer(self, token: str):
        """Build a fake dns.resolver answer with a single TXT record matching token."""
        rdata = MagicMock()
        rdata.strings = [token.encode("utf-8")]
        answers = MagicMock()
        answers.__iter__ = MagicMock(return_value=iter([rdata]))
        return answers

    @pytest.mark.asyncio
    async def test_dns_match_returns_true(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "dns1@test.com")
        token = "rocher-verify-match123"
        record = await _seed_verification(
            db_session, user.id, "match.com", verified=False, token=token
        )
        await db_session.commit()

        answers = self._make_dns_answer(token)

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", return_value=answers),
        ):
            mock_settings.APP_ENV = "production"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is True
        assert record.verified is True

    @pytest.mark.asyncio
    async def test_dns_match_sets_verified_at(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "dns2@test.com")
        token = "rocher-verify-ts456"
        record = await _seed_verification(
            db_session, user.id, "tscheck.com", verified=False, token=token
        )
        await db_session.commit()

        answers = self._make_dns_answer(token)

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", return_value=answers),
        ):
            mock_settings.APP_ENV = "production"
            await phishing_service.check_domain_verification(record, db_session)

        assert isinstance(record.verified_at, datetime)

    @pytest.mark.asyncio
    async def test_dns_query_uses_correct_subdomain(self, db_session: AsyncSession):
        """Resolver must query _rocher-verify.<domain>."""
        user = await _seed_user(db_session, "dns3@test.com")
        token = "rocher-verify-sub789"
        record = await _seed_verification(
            db_session, user.id, "querydomain.com", verified=False, token=token
        )
        await db_session.commit()

        answers = self._make_dns_answer(token)

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", return_value=answers) as mock_resolve,
        ):
            mock_settings.APP_ENV = "production"
            await phishing_service.check_domain_verification(record, db_session)

        call_args = mock_resolve.call_args[0]
        assert call_args[0] == "_rocher-verify.querydomain.com"
        assert call_args[1] == "TXT"


# ---------------------------------------------------------------------------
# 5. check_domain_verification — DNS TXT mismatch
# ---------------------------------------------------------------------------


class TestCheckDomainVerificationDnsMismatch:
    @pytest.mark.asyncio
    async def test_wrong_token_returns_false(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "mm1@test.com")
        record = await _seed_verification(
            db_session, user.id, "mismatch.com", verified=False, token="rocher-verify-correct"
        )
        await db_session.commit()

        rdata = MagicMock()
        rdata.strings = [b"rocher-verify-WRONG"]
        answers = MagicMock()
        answers.__iter__ = MagicMock(return_value=iter([rdata]))

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", return_value=answers),
        ):
            mock_settings.APP_ENV = "production"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is False
        assert record.verified is False

    @pytest.mark.asyncio
    async def test_empty_txt_records_returns_false(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "mm2@test.com")
        record = await _seed_verification(
            db_session, user.id, "empty.com", verified=False, token="rocher-verify-tok"
        )
        await db_session.commit()

        rdata = MagicMock()
        rdata.strings = []
        answers = MagicMock()
        answers.__iter__ = MagicMock(return_value=iter([rdata]))

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", return_value=answers),
        ):
            mock_settings.APP_ENV = "production"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is False


# ---------------------------------------------------------------------------
# 6. check_domain_verification — DNS resolution failure
# ---------------------------------------------------------------------------


class TestCheckDomainVerificationDnsFailure:
    @pytest.mark.asyncio
    async def test_nxdomain_returns_false(self, db_session: AsyncSession):
        import dns.resolver

        user = await _seed_user(db_session, "fail1@test.com")
        record = await _seed_verification(
            db_session, user.id, "nonexistent.example", verified=False, token="rocher-verify-x"
        )
        await db_session.commit()

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", side_effect=dns.resolver.NXDOMAIN()),
        ):
            mock_settings.APP_ENV = "production"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is False
        assert record.verified is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self, db_session: AsyncSession):
        import dns.exception

        user = await _seed_user(db_session, "fail2@test.com")
        record = await _seed_verification(
            db_session, user.id, "slow.example", verified=False, token="rocher-verify-y"
        )
        await db_session.commit()

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", side_effect=dns.exception.Timeout()),
        ):
            mock_settings.APP_ENV = "production"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is False

    @pytest.mark.asyncio
    async def test_generic_exception_returns_false(self, db_session: AsyncSession):
        user = await _seed_user(db_session, "fail3@test.com")
        record = await _seed_verification(
            db_session, user.id, "broken.example", verified=False, token="rocher-verify-z"
        )
        await db_session.commit()

        with (
            patch("app.core.config.settings") as mock_settings,
            patch("dns.resolver.resolve", side_effect=Exception("network error")),
        ):
            mock_settings.APP_ENV = "production"
            result = await phishing_service.check_domain_verification(record, db_session)

        assert result is False
        assert record.verified is False
