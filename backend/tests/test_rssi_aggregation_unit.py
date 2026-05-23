"""Unit tests — rssi_aggregation_service.py."""
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.rssi_aggregation_service import (
    DashboardOverview,
    compute_overview,
    get_clients_summary,
    get_pending_alerts,
    get_upcoming_events,
    compute_suggestions,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_client(
    cid=1,
    name="Acme",
    formula="essentiel",
    monthly_amount=500.0,
    status="active",
    contract_renewal_at=None,
    contract_start_date=None,
):
    c = MagicMock()
    c.id = cid
    c.name = name
    c.formula = formula
    c.monthly_amount = monthly_amount
    c.status = status
    c.contract_renewal_at = contract_renewal_at
    c.contract_start_date = contract_start_date
    c.created_at = date.today()
    return c


def _make_action(aid=1, client_id=1, status="open", priority="medium", due_date=None):
    a = MagicMock()
    a.id = aid
    a.client_id = client_id
    a.status = status
    a.priority = priority
    a.title = f"Action {aid}"
    a.due_date = due_date
    return a


def _make_visit(vid=1, client_id=1, status="planned", scheduled_date=None, actual_date=None, visit_type="audit", location="Sur site"):
    v = MagicMock()
    v.id = vid
    v.client_id = client_id
    v.status = status
    v.scheduled_date = scheduled_date or (date.today() + timedelta(days=7))
    v.actual_date = actual_date
    v.visit_type = visit_type
    v.location = location
    return v


def _db_multi(*result_sequences):
    """DB mock that returns each sequence in order for successive execute() calls."""
    db = AsyncMock()
    call_count = [0]

    async def execute(q):
        i = call_count[0]
        call_count[0] += 1
        if i >= len(result_sequences):
            r = MagicMock()
            r.scalars.return_value.all.return_value = []
            return r
        items = result_sequences[i]
        r = MagicMock()
        r.scalars.return_value.all.return_value = items
        return r

    db.execute = execute
    return db


# ── DashboardOverview.dict ─────────────────────────────────────────────────────

def test_dashboard_overview_dict():
    ov = DashboardOverview(
        total_clients=3,
        total_mrr=1500.0,
        open_actions=5,
        overdue_actions=2,
        renewals_upcoming=1,
        upcoming_visits=2,
    )
    d = ov.dict()
    assert d["total_clients"] == 3
    assert d["total_mrr"] == 1500.0
    assert d["open_actions"] == 5
    assert d["overdue_actions"] == 2
    assert d["renewals_upcoming"] == 1
    assert d["upcoming_visits"] == 2


# ── compute_overview ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_overview_no_clients():
    db = _db_multi([])
    result = await compute_overview(consultant_id=1, db=db)
    assert result.total_clients == 0
    assert result.total_mrr == 0.0
    assert result.open_actions == 0
    assert result.overdue_actions == 0


@pytest.mark.asyncio
async def test_compute_overview_with_clients_no_actions():
    clients = [
        _make_client(1, "Acme", monthly_amount=500.0),
        _make_client(2, "Corp", monthly_amount=750.0),
    ]
    # clients, actions, visits
    db = _db_multi(clients, [], [])
    result = await compute_overview(consultant_id=1, db=db)
    assert result.total_clients == 2
    assert result.total_mrr == 1250.0
    assert result.open_actions == 0


@pytest.mark.asyncio
async def test_compute_overview_overdue_actions():
    today = date.today()
    clients = [_make_client(1)]
    past = today - timedelta(days=3)
    actions = [
        _make_action(1, client_id=1, status="open", due_date=past),   # overdue
        _make_action(2, client_id=1, status="open", due_date=today + timedelta(days=5)),  # not overdue
    ]
    db = _db_multi(clients, actions, [])
    result = await compute_overview(1, db)
    assert result.open_actions == 2
    assert result.overdue_actions == 1


@pytest.mark.asyncio
async def test_compute_overview_renewal_upcoming():
    today = date.today()
    renewing = _make_client(1, contract_renewal_at=today + timedelta(days=30))
    not_renewing = _make_client(2, contract_renewal_at=today + timedelta(days=90))
    db = _db_multi([renewing, not_renewing], [], [])
    result = await compute_overview(1, db)
    assert result.renewals_upcoming == 1


@pytest.mark.asyncio
async def test_compute_overview_upcoming_visits():
    clients = [_make_client(1)]
    visits = [_make_visit(1, client_id=1, status="planned")]
    db = _db_multi(clients, [], visits)
    result = await compute_overview(1, db)
    assert result.upcoming_visits == 1


@pytest.mark.asyncio
async def test_compute_overview_no_monthly_amount():
    clients = [_make_client(1, monthly_amount=None)]
    db = _db_multi(clients, [], [])
    result = await compute_overview(1, db)
    assert result.total_mrr == 0.0


# ── get_clients_summary ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_clients_summary_empty():
    db = _db_multi([])
    result = await get_clients_summary(1, db)
    assert result == []


@pytest.mark.asyncio
async def test_get_clients_summary_basic():
    today = date.today()
    clients = [_make_client(1, "Acme", formula="essentiel", monthly_amount=500.0)]
    clients[0].contract_renewal_at = None
    db = _db_multi(clients, [], [])
    result = await get_clients_summary(1, db)
    assert len(result) == 1
    assert result[0]["name"] == "Acme"
    assert result[0]["open_actions"] == 0
    assert result[0]["overdue_actions"] == 0
    assert result[0]["next_visit"] is None


@pytest.mark.asyncio
async def test_get_clients_summary_with_actions_and_visit():
    today = date.today()
    clients = [_make_client(1, "Corp")]
    clients[0].contract_renewal_at = today + timedelta(days=30)
    actions = [
        _make_action(1, client_id=1, due_date=today - timedelta(days=2)),  # overdue
        _make_action(2, client_id=1, due_date=today + timedelta(days=5)),
    ]
    next_visit_date = today + timedelta(days=3)
    visits = [_make_visit(1, client_id=1, scheduled_date=next_visit_date)]
    db = _db_multi(clients, actions, visits)
    result = await get_clients_summary(1, db)
    assert result[0]["open_actions"] == 2
    assert result[0]["overdue_actions"] == 1
    assert result[0]["next_visit"] == next_visit_date.isoformat()


# ── get_pending_alerts ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_pending_alerts_empty():
    db = _db_multi([])
    result = await get_pending_alerts(1, db)
    assert result == []


@pytest.mark.asyncio
async def test_get_pending_alerts_overdue_action():
    today = date.today()
    clients = [_make_client(1, "Acme")]
    past = today - timedelta(days=5)
    actions = [_make_action(1, client_id=1, priority="high", due_date=past)]
    premium_visits: list = []
    db = _db_multi(clients, actions, premium_visits)
    result = await get_pending_alerts(1, db)
    overdue = [a for a in result if a["type"] == "overdue_action"]
    assert len(overdue) == 1
    assert overdue[0]["severity"] == "high"


@pytest.mark.asyncio
async def test_get_pending_alerts_renewal():
    today = date.today()
    client = _make_client(1, "Renewing Corp", contract_renewal_at=today + timedelta(days=25))
    db = _db_multi([client], [], [])
    result = await get_pending_alerts(1, db)
    renewals = [a for a in result if a["type"] == "renewal_upcoming"]
    assert len(renewals) == 1
    assert renewals[0]["severity"] == "high"  # 25 days → high


@pytest.mark.asyncio
async def test_get_pending_alerts_no_recent_visit_premium():
    today = date.today()
    client = _make_client(1, "Premium Client", formula="premium")
    # last visit was 40 days ago → triggers alert
    old_visit = _make_visit(1, client_id=1, status="completed",
                            actual_date=today - timedelta(days=40))
    db = _db_multi([client], [], [old_visit])
    result = await get_pending_alerts(1, db)
    no_visit_alerts = [a for a in result if a["type"] == "no_recent_visit"]
    assert len(no_visit_alerts) == 1


@pytest.mark.asyncio
async def test_get_pending_alerts_recent_visit_no_alert():
    today = date.today()
    client = _make_client(1, "Active Premium", formula="premium")
    recent_visit = _make_visit(1, client_id=1, status="completed",
                               actual_date=today - timedelta(days=10))
    db = _db_multi([client], [], [recent_visit])
    result = await get_pending_alerts(1, db)
    no_visit_alerts = [a for a in result if a["type"] == "no_recent_visit"]
    assert len(no_visit_alerts) == 0


# ── get_upcoming_events ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_upcoming_events_no_clients():
    db = _db_multi([])
    result = await get_upcoming_events(1, days_ahead=14, db=db)
    assert result == []


@pytest.mark.asyncio
async def test_get_upcoming_events_with_visits():
    today = date.today()
    clients = [_make_client(1, "Acme")]
    visits = [_make_visit(1, client_id=1, scheduled_date=today + timedelta(days=5),
                          visit_type="audit", location="Sur site")]
    db = _db_multi(clients, visits)
    result = await get_upcoming_events(1, days_ahead=14, db=db)
    assert len(result) == 1
    assert result[0]["client_name"] == "Acme"
    assert result[0]["visit_type"] == "audit"


# ── compute_suggestions ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_compute_suggestions_no_clients():
    db = _db_multi([])
    result = await compute_suggestions(1, db)
    assert result == []


@pytest.mark.asyncio
async def test_compute_suggestions_upsell():
    today = date.today()
    client = _make_client(
        1, "Stable Essentiel",
        formula="essentiel",
        contract_start_date=today - timedelta(days=200),  # > 180 days
    )
    db = _db_multi([client], [], [])
    result = await compute_suggestions(1, db)
    upsell = [s for s in result if s["type"] == "upsell_opportunity"]
    assert len(upsell) == 1


@pytest.mark.asyncio
async def test_compute_suggestions_no_upsell_with_overdue():
    today = date.today()
    client = _make_client(
        1, "Overdue Essentiel",
        formula="essentiel",
        contract_start_date=today - timedelta(days=200),
    )
    actions = [_make_action(1, client_id=1, due_date=today - timedelta(days=5))]
    db = _db_multi([client], actions, [])
    result = await compute_suggestions(1, db)
    # overdue action blocks upsell suggestion
    upsell = [s for s in result if s["type"] == "upsell_opportunity"]
    assert len(upsell) == 0


@pytest.mark.asyncio
async def test_compute_suggestions_engagement_alert():
    today = date.today()
    client = _make_client(1, "Premium Unvisited", formula="premium")
    # No visits → triggers engagement alert
    db = _db_multi([client], [], [])
    result = await compute_suggestions(1, db)
    engagement = [s for s in result if s["type"] == "engagement_alert"]
    assert len(engagement) == 1


@pytest.mark.asyncio
async def test_compute_suggestions_renewal():
    today = date.today()
    client = _make_client(1, "Renewing", contract_renewal_at=today + timedelta(days=45))
    db = _db_multi([client], [], [])
    result = await compute_suggestions(1, db)
    renewal = [s for s in result if s["type"] == "renewal_upcoming"]
    assert len(renewal) == 1
    assert "45 jour(s)" in renewal[0]["title"]


@pytest.mark.asyncio
async def test_compute_suggestions_high_overdue():
    today = date.today()
    client = _make_client(1, "Lagging Corp")
    past = today - timedelta(days=10)
    actions = [_make_action(i, client_id=1, due_date=past) for i in range(1, 5)]  # 4 overdue
    db = _db_multi([client], actions, [])
    result = await compute_suggestions(1, db)
    overdue = [s for s in result if s["type"] == "high_overdue"]
    assert len(overdue) == 1
    assert "4 actions" in overdue[0]["title"]
