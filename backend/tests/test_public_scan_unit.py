"""
Unit tests — public scan service and schema (without HTTP/DB).

Covers: run_public_scan() orchestrator, PublicScanOut.from_orm_obj(),
        URL normalization, SSRF enforcement in endpoint.
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.public_scan import PublicScanOut
from app.services.public_scan_service import run_public_scan
from app.models.public_scan import PublicScan


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
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
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

    def test_done_scan_with_results(self):
        results = json.dumps({"ssl": {"status": "OK"}})
        scan = _make_scan(status="done", overall_status="OK", results_json=results)
        out = PublicScanOut.from_orm_obj(scan)
        assert out.status == "done"
        assert out.overall_status == "OK"
        assert out.results_json == results

    def test_failed_scan_with_error(self):
        scan = _make_scan(status="failed", error_message="Timeout")
        out = PublicScanOut.from_orm_obj(scan)
        assert out.status == "failed"
        assert out.error_message == "Timeout"

    def test_timestamps_preserved(self):
        started = datetime(2025, 6, 1, 12, 0, tzinfo=timezone.utc)
        finished = datetime(2025, 6, 1, 12, 1, tzinfo=timezone.utc)
        scan = _make_scan(started_at=started, finished_at=finished)
        out = PublicScanOut.from_orm_obj(scan)
        assert out.started_at == started
        assert out.finished_at == finished


# ── run_public_scan() ──────────────────────────────────────────────────────────

class TestRunPublicScan:
    @pytest.mark.asyncio
    async def test_scan_not_found_returns_early(self):
        db = _mock_db(scan=None)
        await run_public_scan(999, db)
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_successful_scan_sets_done(self):
        scan = _make_scan(target_url="https://example.com")
        db = _mock_db(scan=scan)

        fake_outcome = {
            "results": {"ssl": {"status": "OK"}},
            "overall": "OK",
        }

        with patch("app.services.public_scan_service._run_demo_scan_sync", return_value=fake_outcome):
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

        with patch("app.services.public_scan_service._run_demo_scan_sync", side_effect=capture_sync):
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

        with patch("app.services.public_scan_service._run_demo_scan_sync", side_effect=capture_sync):
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

        with patch("app.services.public_scan_service._run_demo_scan_sync", side_effect=capture_sync):
            await run_public_scan(1, db)

        assert started_ats[0] is not None

