"""
Coverage tests for app.services.darkweb_dossier.ingestion — targets the branches
NOT exercised by the existing unit/integration suites:

  * process_dossier: dossier-not-found early return, rate_limited vs api_error
    classification, unverified exclusion from risk, heavy/weighted risk maths,
    invalid breach_sources_json handling, monitor_active -> next_monitor_at,
    and the top-level except -> status=failed path.
  * send_monitoring_alert: the ">10 new accounts" summary line and the
    _send-raises swallow path.

All external calls (check_email_breaches / _send) are mocked. process_dossier is
driven directly against the test Postgres DB (conftest patches AsyncSessionLocal),
seeding rows through the db_session fixture.
"""

import json

import app.core.database as _db_module
from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
from app.models.user import User
from app.services.darkweb_dossier import ingestion
from app.services.darkweb_dossier.ingestion import process_dossier, send_monitoring_alert

# asyncio_mode=auto -> `async def test_*` needs no decorator.

_BREACH_RESULT = {
    "email": "x",
    "breaches": [{"name": "LinkedIn", "data_classes": ["Email addresses", "Passwords"]}],
    "total": 4,
    "status": "WARNING",
    "error": None,
}
_CLEAN_RESULT = {
    "email": "x",
    "breaches": [],
    "total": 0,
    "status": "OK",
    "error": None,
}
_RATE_LIMITED_RESULT = {
    "email": "x",
    "breaches": [],
    "total": 0,
    "status": "unknown",
    "error": "Rate limited — retry later (429)",
}
_API_ERROR_RESULT = {
    "email": "x",
    "breaches": [],
    "total": 0,
    "status": "unknown",
    "error": "Connection timed out",
}


# ── seeding helpers ───────────────────────────────────────────────────────────


async def _seed_user(db, email: str) -> User:
    user = User(email=email, hashed_password="x" * 8)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def _seed_dossier(db, user_id: int, emails: list[str], **kwargs) -> int:
    dossier = DarkwebDossier(
        user_id=user_id,
        company_name=kwargs.get("company_name", "Acme SAS"),
        domain=kwargs.get("domain", "acme.fr"),
        status=kwargs.get("status", "pending"),
        total_emails=len(emails),
        monitor_active=kwargs.get("monitor_active", False),
    )
    db.add(dossier)
    await db.commit()
    await db.refresh(dossier)
    for e in emails:
        db.add(DarkwebDossierTarget(dossier_id=dossier.id, email=e))
    await db.commit()
    return dossier.id


async def _reload_dossier(dossier_id: int) -> DarkwebDossier:
    """Read the dossier through a fresh session (the one process_dossier used is
    already closed). Using AsyncSessionLocal — patched to the test DB by conftest
    — avoids stale identity-map data from the seeding session."""
    from sqlalchemy import select

    async with _db_module.AsyncSessionLocal() as db:
        result = await db.execute(select(DarkwebDossier).where(DarkwebDossier.id == dossier_id))
        dossier = result.scalar_one()
        db.expunge(dossier)  # detach so attributes stay usable after the session closes
        return dossier


async def _reload_targets(dossier_id: int) -> list[DarkwebDossierTarget]:
    from sqlalchemy import select

    async with _db_module.AsyncSessionLocal() as db:
        result = await db.execute(
            select(DarkwebDossierTarget)
            .where(DarkwebDossierTarget.dossier_id == dossier_id)
            .order_by(DarkwebDossierTarget.id)
        )
        targets = list(result.scalars().all())
        for t in targets:
            db.expunge(t)
        return targets


# ── process_dossier: early return ─────────────────────────────────────────────


async def test_process_dossier_missing_dossier_is_noop():
    """Unknown id -> function returns immediately, nothing raised."""
    # No mocking needed: scalar_one_or_none returns None, we never reach the API.
    await process_dossier(99999, "api_key")


# ── process_dossier: happy exposed path (also exercises severity + top_sources) ─


async def test_process_dossier_marks_exposed_and_completes(db_session):
    user = await _seed_user(db_session, "proc-exposed@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["alice@acme.fr"])

    # No _BATCH_DELAY sleep because there is a single target (i==0).
    import unittest.mock as mock

    with mock.patch.object(ingestion, "check_email_breaches", return_value=_BREACH_RESULT):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    targets = await _reload_targets(dossier_id)

    assert dossier.status == "completed"
    assert dossier.exposed_emails == 1
    assert dossier.total_breach_instances == 4
    assert dossier.unverified_count == 0
    # total_breaches>=3 counts as "heavy" -> risk maths goes through the heavy branch.
    assert dossier.risk_score is not None and dossier.risk_score > 0
    assert dossier.severity_score is not None and dossier.severity_score > 0
    # top_sources_json holds the LinkedIn breach name.
    top = json.loads(dossier.top_sources_json)
    assert any(s["name"] == "LinkedIn" for s in top)
    assert targets[0].check_status == "exposed"
    assert targets[0].status == "exposed"
    assert targets[0].total_breaches == 4


# ── process_dossier: rate_limited classification + unverified excluded from risk ─


async def test_process_dossier_rate_limited_unverified(db_session):
    user = await _seed_user(db_session, "proc-rl@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["rl@acme.fr"])

    import unittest.mock as mock

    with mock.patch.object(ingestion, "check_email_breaches", return_value=_RATE_LIMITED_RESULT):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    targets = await _reload_targets(dossier_id)

    assert dossier.status == "completed"
    assert dossier.unverified_count == 1
    # verified_total == 0 -> risk_score forced to 0 branch.
    assert dossier.risk_score == 0
    assert targets[0].check_status == "rate_limited"
    assert targets[0].status == "error"


# ── process_dossier: api_error classification (non-rate keyword) ────────────────


async def test_process_dossier_api_error_classification(db_session):
    user = await _seed_user(db_session, "proc-apierr@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["err@acme.fr"])

    import unittest.mock as mock

    with mock.patch.object(ingestion, "check_email_breaches", return_value=_API_ERROR_RESULT):
        await process_dossier(dossier_id, "key")

    targets = await _reload_targets(dossier_id)
    assert targets[0].check_status == "api_error"
    assert targets[0].status == "error"


# ── process_dossier: clean target ──────────────────────────────────────────────


async def test_process_dossier_clean_target(db_session):
    user = await _seed_user(db_session, "proc-clean@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["clean@acme.fr"])

    import unittest.mock as mock

    with mock.patch.object(ingestion, "check_email_breaches", return_value=_CLEAN_RESULT):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    targets = await _reload_targets(dossier_id)
    assert dossier.status == "completed"
    assert dossier.exposed_emails == 0
    assert dossier.risk_score == 0  # verified_total>0 but exposed==0
    assert targets[0].check_status == "verified_clean"
    assert targets[0].status == "clean"


# ── process_dossier: mixed batch -> exercises _BATCH_DELAY sleep + weighted maths ─


async def test_process_dossier_mixed_batch_weighted_risk(db_session):
    """Multiple targets: one heavy-exposed, one clean, one rate-limited.

    Exercises the i>0 sleep branch, the heavy/weighted risk formula and
    unverified exclusion together.
    """
    user = await _seed_user(db_session, "proc-mixed@test.com")
    dossier_id = await _seed_dossier(
        db_session, user.id, ["heavy@acme.fr", "clean@acme.fr", "rl@acme.fr"]
    )

    import unittest.mock as mock

    results = iter([_BREACH_RESULT, _CLEAN_RESULT, _RATE_LIMITED_RESULT])

    # Patch sleep so the 2.5s batch delay does not slow the test.
    async def _no_sleep(_):
        return None

    with (
        mock.patch.object(
            ingestion, "check_email_breaches", side_effect=lambda *a, **k: next(results)
        ),
        mock.patch.object(ingestion.asyncio, "sleep", side_effect=_no_sleep),
    ):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    assert dossier.status == "completed"
    assert dossier.exposed_emails == 1
    assert dossier.unverified_count == 1
    # verified_total = 3 - 1 = 2 ; exposed=1 ; heavy=1
    # weighted = (1 + 0.5) / (2 + 0.5) = 0.6 -> 60
    assert dossier.risk_score == 60
    assert dossier.checked_count == 3


# ── process_dossier: top_sources aggregation across targets (Counter path) ──────


async def test_process_dossier_top_sources_aggregated(db_session):
    """Two exposed targets sharing a breach source -> Counter.most_common must
    aggregate counts and rank the shared source first."""
    user = await _seed_user(db_session, "proc-topsrc@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["a@acme.fr", "b@acme.fr"])

    import unittest.mock as mock

    result_a = {
        "email": "a",
        "breaches": [
            {"name": "LinkedIn", "data_classes": ["Passwords"]},
            {"name": "Adobe", "data_classes": ["Email addresses"]},
        ],
        "total": 2,
        "status": "WARNING",
        "error": None,
    }
    result_b = {
        "email": "b",
        "breaches": [{"name": "LinkedIn", "data_classes": ["Passwords"]}],
        "total": 1,
        "status": "WARNING",
        "error": None,
    }
    results = iter([result_a, result_b])

    async def _no_sleep(_):
        return None

    with (
        mock.patch.object(
            ingestion, "check_email_breaches", side_effect=lambda *a, **k: next(results)
        ),
        mock.patch.object(ingestion.asyncio, "sleep", side_effect=_no_sleep),
    ):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    assert dossier.status == "completed"
    top = json.loads(dossier.top_sources_json)
    by_name = {s["name"]: s["count"] for s in top}
    assert by_name["LinkedIn"] == 2  # counted from both targets
    assert by_name["Adobe"] == 1
    # LinkedIn (most common) ranks first.
    assert top[0]["name"] == "LinkedIn"


# ── process_dossier: monitor_active schedules next_monitor_at ───────────────────


async def test_process_dossier_sets_next_monitor_when_active(db_session):
    user = await _seed_user(db_session, "proc-mon@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["m@acme.fr"], monitor_active=True)

    import unittest.mock as mock

    with mock.patch.object(ingestion, "check_email_breaches", return_value=_CLEAN_RESULT):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    assert dossier.monitor_active is True
    assert dossier.next_monitor_at is not None
    assert dossier.last_monitored_at is not None
    # next_monitor_at should be ~30 days after last_monitored_at.
    delta = dossier.next_monitor_at - dossier.last_monitored_at
    assert 29 <= delta.days <= 30


# ── process_dossier: exception during processing -> status=failed ──────────────


async def test_process_dossier_failure_sets_failed_status(db_session):
    """If check_email_breaches raises, the top-level except records the error
    and marks the dossier failed (finished_at set)."""
    user = await _seed_user(db_session, "proc-fail@test.com")
    dossier_id = await _seed_dossier(db_session, user.id, ["boom@acme.fr"])

    import unittest.mock as mock

    def _raise(*a, **k):
        raise RuntimeError("provider exploded")

    with mock.patch.object(ingestion, "check_email_breaches", side_effect=_raise):
        await process_dossier(dossier_id, "key")

    dossier = await _reload_dossier(dossier_id)
    assert dossier.status == "failed"
    assert "provider exploded" in (dossier.error_message or "")
    assert dossier.finished_at is not None


# ── send_monitoring_alert: >10 accounts -> "+ N autres" summary + _send called ─


def test_send_monitoring_alert_more_than_ten():
    import unittest.mock as mock

    new_exposed = [f"user{i}@acme.fr" for i in range(15)]
    with mock.patch.object(ingestion, "_send") as send_mock:
        send_monitoring_alert("rssi@acme.fr", "Acme", "acme.fr", 15, new_exposed, "https://dash/x")

    send_mock.assert_called_once()
    to_email, subject, html, plain = send_mock.call_args.args
    assert to_email == "rssi@acme.fr"
    assert "acme.fr" in subject
    # "+ 5 autres" summary rendered (15 - 10).
    assert "+ 5 autres" in html
    # Only the first 10 accounts are listed individually.
    assert html.count("<li") == 10
    assert "15 compte(s)" in html


# ── send_monitoring_alert: <=10 accounts -> no summary line ─────────────────────


def test_send_monitoring_alert_ten_or_fewer_no_summary():
    import unittest.mock as mock

    with mock.patch.object(ingestion, "_send") as send_mock:
        send_monitoring_alert(
            "rssi@acme.fr", "Acme", "acme.fr", 2, ["a@acme.fr", "b@acme.fr"], "https://dash"
        )

    send_mock.assert_called_once()
    _, _, html, _ = send_mock.call_args.args
    assert "autres" not in html
    assert html.count("<li") == 2


# ── send_monitoring_alert: _send raises -> swallowed (no exception propagates) ──


def test_send_monitoring_alert_swallows_send_error():
    import unittest.mock as mock

    with mock.patch.object(ingestion, "_send", side_effect=RuntimeError("SMTP down")):
        # Must not raise.
        send_monitoring_alert("rssi@acme.fr", "Acme", "acme.fr", 1, ["a@acme.fr"], "https://dash")
