"""
Unit tests — public scan service and schema (without HTTP/DB).

Covers: run_public_scan() orchestrator, PublicScanOut.from_orm_obj(),
        URL normalization, SSRF enforcement in endpoint.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.public_scan import PublicScan
from app.schemas.public_scan import PublicScanOut
from app.services import public_scan_service
from app.services.public_scan_service import (
    MAX_DOMAINS_PER_EMAIL,
    QuotaExceededError,
    ScanNotReadyError,
    _domain_of,
    compute_severity_counts,
    hash_ip,
    run_public_scan,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_scan(**kwargs) -> MagicMock:
    defaults = dict(
        id=1,
        session_token="abc123",
        target_url="https://example.com",
        status="pending",
        overall_status=None,
        results_json=None,
        error_message=None,
        email=None,
        email_consent_at=None,
        ip_hash=None,
        domain=None,
        created_at=datetime(2025, 1, 1, tzinfo=UTC),
        started_at=None,
        finished_at=None,
    )
    defaults.update(kwargs)
    scan = MagicMock(spec=PublicScan)
    for k, v in defaults.items():
        setattr(scan, k, v)
    return scan


def _mock_db(scan=None) -> AsyncMock:
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = scan
    db.execute = AsyncMock(return_value=mock_result)
    db.commit = AsyncMock()
    return db


# ── PublicScanOut.from_orm_obj() ───────────────────────────────────────────────


class TestPublicScanOutSchema:
    def test_pending_scan(self):
        scan = _make_scan(status="pending")
        out = PublicScanOut.from_orm_obj(scan)
        assert out.token == "abc123"
        assert out.status == "pending"
        assert out.overall_status is None
        assert out.results_json is None

    def test_done_scan_locked_hides_results(self):
        """Un scan terminé mais non débloqué (email absent) est verrouillé : le teaser
        n'expose pas results_json."""
        results = json.dumps({"ssl": {"status": "OK"}})
        scan = _make_scan(
            status="done", overall_status="OK", results_json=results, email_consent_at=None
        )
        out = PublicScanOut.from_orm_obj(scan)
        assert out.status == "done"
        assert out.overall_status == "OK"
        assert out.locked is True
        assert out.results_json is None

    def test_done_scan_unlocked_reveals_results(self):
        """Une fois le consentement posé, le rapport complet est révélé."""
        results = json.dumps({"ssl": {"status": "OK"}})
        scan = _make_scan(
            status="done",
            overall_status="OK",
            results_json=results,
            email="lead@example.com",
            email_consent_at=datetime(2025, 2, 1, tzinfo=UTC),
        )
        out = PublicScanOut.from_orm_obj(scan)
        assert out.status == "done"
        assert out.locked is False
        assert out.results_json == results

    def test_severity_counts_passed_through(self):
        scan = _make_scan(status="done", overall_status="WARNING")
        out = PublicScanOut.from_orm_obj(
            scan, severity_counts={"CRITICAL": 1, "WARNING": 2, "OK": 6}
        )
        assert out.severity_counts == {"CRITICAL": 1, "WARNING": 2, "OK": 6}

    def test_failed_scan_with_error(self):
        scan = _make_scan(status="failed", error_message="Timeout")
        out = PublicScanOut.from_orm_obj(scan)
        assert out.status == "failed"
        assert out.error_message == "Timeout"

    def test_timestamps_preserved(self):
        started = datetime(2025, 6, 1, 12, 0, tzinfo=UTC)
        finished = datetime(2025, 6, 1, 12, 1, tzinfo=UTC)
        scan = _make_scan(started_at=started, finished_at=finished)
        out = PublicScanOut.from_orm_obj(scan)
        assert out.started_at == started
        assert out.finished_at == finished


# ── run_public_scan() ──────────────────────────────────────────────────────────


class TestRunPublicScan:
    @pytest.fixture(autouse=True)
    def _no_ssrf(self):
        """Neutralise la re-validation SSRF (pas d'appel DNS reel en test unitaire).
        Les tests qui veulent verifier le blocage la reconfigurent via side_effect."""
        with patch("app.services.public_scan_service.assert_no_ssrf") as m:
            yield m

    @pytest.mark.asyncio
    async def test_scan_not_found_returns_early(self):
        db = _mock_db(scan=None)
        await run_public_scan(999, db)
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_ssrf_revalidation_blocks_scan_at_execution(self, _no_ssrf):
        """Si le DNS a bascule vers une IP interne entre la creation et l'execution,
        assert_no_ssrf leve -> le scan est marque failed sans lancer les sondes."""
        _no_ssrf.side_effect = HTTPException(status_code=422, detail="interne")
        scan = _make_scan(target_url="https://rebind.example.com")
        db = _mock_db(scan=scan)

        with patch("app.services.public_scan_service._run_demo_scan_sync") as run_sync:
            await run_public_scan(1, db)

        run_sync.assert_not_called()
        assert scan.status == "failed"
        assert "interne" in scan.error_message
        assert scan.finished_at is not None
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_successful_scan_sets_done(self):
        scan = _make_scan(target_url="https://example.com")
        db = _mock_db(scan=scan)

        fake_outcome = {
            "results": {"ssl": {"status": "OK"}},
            "overall": "OK",
        }

        with patch(
            "app.services.public_scan_service._run_demo_scan_sync",
            return_value=fake_outcome,
        ):
            await run_public_scan(1, db)

        assert scan.status == "done"
        assert scan.overall_status == "OK"
        assert json.loads(scan.results_json) == fake_outcome["results"]
        assert scan.finished_at is not None
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_scan_failure_sets_failed_status(self):
        scan = _make_scan(target_url="https://example.com")
        db = _mock_db(scan=scan)

        with patch(
            "app.services.public_scan_service._run_demo_scan_sync",
            side_effect=RuntimeError("connection refused"),
        ):
            await run_public_scan(1, db)

        assert scan.status == "failed"
        assert "connection refused" in scan.error_message
        assert scan.finished_at is not None
        db.commit.assert_called()

    @pytest.mark.asyncio
    async def test_running_status_set_before_executor(self):
        scan = _make_scan(target_url="https://example.com")
        db = _mock_db(scan=scan)
        statuses = []

        def capture_sync(url):
            statuses.append(scan.status)
            return {"results": {}, "overall": "OK"}

        with patch(
            "app.services.public_scan_service._run_demo_scan_sync",
            side_effect=capture_sync,
        ):
            await run_public_scan(1, db)

        assert statuses[0] == "running"

    @pytest.mark.asyncio
    async def test_url_without_scheme_gets_https(self):
        scan = _make_scan(target_url="example.com")
        db = _mock_db(scan=scan)
        called_with = []

        def capture_sync(url):
            called_with.append(url)
            return {"results": {}, "overall": "OK"}

        with patch(
            "app.services.public_scan_service._run_demo_scan_sync",
            side_effect=capture_sync,
        ):
            await run_public_scan(1, db)

        assert called_with[0] == "https://example.com"

    @pytest.mark.asyncio
    async def test_error_message_truncated_to_512(self):
        scan = _make_scan(target_url="https://example.com")
        db = _mock_db(scan=scan)
        long_error = "x" * 1000

        with patch(
            "app.services.public_scan_service._run_demo_scan_sync",
            side_effect=RuntimeError(long_error),
        ):
            await run_public_scan(1, db)

        assert len(scan.error_message) <= 512

    @pytest.mark.asyncio
    async def test_started_at_set_before_scan(self):
        scan = _make_scan(target_url="https://example.com")
        db = _mock_db(scan=scan)
        started_ats = []

        def capture_sync(url):
            started_ats.append(scan.started_at)
            return {"results": {}, "overall": "OK"}

        with patch(
            "app.services.public_scan_service._run_demo_scan_sync",
            side_effect=capture_sync,
        ):
            await run_public_scan(1, db)

        assert started_ats[0] is not None


# ── Fonctions pures du gate lead ────────────────────────────────────────────────


class TestGateHelpers:
    def test_hash_ip_deterministic_and_hex64(self):
        h1 = hash_ip("203.0.113.7")
        h2 = hash_ip("203.0.113.7")
        assert h1 == h2
        assert len(h1) == 64
        assert h1 != "203.0.113.7"  # jamais l'IP en clair

    def test_hash_ip_differs_per_ip(self):
        assert hash_ip("203.0.113.7") != hash_ip("203.0.113.8")

    def test_domain_of_extracts_hostname_lowercased(self):
        assert _domain_of("https://Example.COM/path?q=1") == "example.com"
        assert _domain_of("example.com") == "example.com"
        assert _domain_of("http://sub.example.com") == "sub.example.com"

    def test_compute_severity_counts_aggregates(self):
        scan = _make_scan(
            results_json=json.dumps(
                {
                    "ssl": {"status": "OK"},
                    "headers": {"status": "WARNING"},
                    "cors": {"status": "CRITICAL"},
                    "dns": {"status": "OK"},
                    "_meta": {"url": "https://example.com"},
                }
            )
        )
        assert compute_severity_counts(scan) == {"CRITICAL": 1, "WARNING": 1, "OK": 2}

    def test_compute_severity_counts_none_when_no_results(self):
        assert compute_severity_counts(_make_scan(results_json=None)) is None

    def test_compute_severity_counts_none_on_bad_json(self):
        assert compute_severity_counts(_make_scan(results_json="not-json")) is None


# ── unlock_public_scan() sur DB réelle ──────────────────────────────────────────


async def _seed_scan(db, *, target_url, status="done", results_json=None):
    scan = PublicScan(target_url=target_url, status=status, results_json=results_json)
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    return scan


class TestUnlockPublicScan:
    @pytest.mark.asyncio
    async def test_unknown_token_returns_none(self, db_session):
        result = await public_scan_service.unlock_public_scan(
            db_session, token="does-not-exist", email="a@b.com", ip_hash="h"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_not_done_raises_scan_not_ready(self, db_session):
        scan = await _seed_scan(db_session, target_url="https://a.example.com", status="running")
        with pytest.raises(ScanNotReadyError):
            await public_scan_service.unlock_public_scan(
                db_session, token=scan.session_token, email="a@b.com", ip_hash="h"
            )

    @pytest.mark.asyncio
    async def test_unlock_sets_lead_fields(self, db_session):
        scan = await _seed_scan(
            db_session,
            target_url="https://a.example.com",
            results_json=json.dumps({"ssl": {"status": "OK"}}),
        )
        out = await public_scan_service.unlock_public_scan(
            db_session, token=scan.session_token, email="Lead@Example.com ", ip_hash="hashval"
        )
        assert out is not None
        assert out.email == "lead@example.com"  # normalisé
        assert out.email_consent_at is not None
        assert out.ip_hash == "hashval"
        assert out.domain == "a.example.com"

    @pytest.mark.asyncio
    async def test_unlock_idempotent_same_email(self, db_session):
        scan = await _seed_scan(db_session, target_url="https://a.example.com")
        first = await public_scan_service.unlock_public_scan(
            db_session, token=scan.session_token, email="lead@example.com", ip_hash="h1"
        )
        consent_at = first.email_consent_at
        again = await public_scan_service.unlock_public_scan(
            db_session, token=scan.session_token, email="lead@example.com", ip_hash="h2"
        )
        assert again.email_consent_at == consent_at  # pas ré-écrit

    @pytest.mark.asyncio
    async def test_quota_blocks_after_max_domains(self, db_session):
        email = "lead@example.com"
        # Débloque MAX_DOMAINS_PER_EMAIL domaines distincts.
        for i in range(MAX_DOMAINS_PER_EMAIL):
            scan = await _seed_scan(db_session, target_url=f"https://site{i}.example.com")
            await public_scan_service.unlock_public_scan(
                db_session, token=scan.session_token, email=email, ip_hash="h"
            )
        # Un domaine de plus dépasse le plafond.
        extra = await _seed_scan(db_session, target_url="https://one-too-many.example.com")
        with pytest.raises(QuotaExceededError):
            await public_scan_service.unlock_public_scan(
                db_session, token=extra.session_token, email=email, ip_hash="h"
            )

    @pytest.mark.asyncio
    async def test_same_domain_does_not_consume_quota(self, db_session):
        email = "lead@example.com"
        for i in range(MAX_DOMAINS_PER_EMAIL):
            scan = await _seed_scan(db_session, target_url=f"https://site{i}.example.com")
            await public_scan_service.unlock_public_scan(
                db_session, token=scan.session_token, email=email, ip_hash="h"
            )
        # Nouveau scan mais domaine DÉJÀ débloqué → autorisé malgré le plafond.
        again = await _seed_scan(db_session, target_url="https://site0.example.com/other-page")
        out = await public_scan_service.unlock_public_scan(
            db_session, token=again.session_token, email=email, ip_hash="h"
        )
        assert out is not None
        assert out.domain == "site0.example.com"
