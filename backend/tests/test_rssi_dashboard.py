"""
Integration tests — /api/v1/rssi/dashboard (Sprint 2)
Covers: overview, clients-summary, alerts, upcoming-events, suggestions, auth guards.
"""
import pytest
from datetime import date, timedelta
from httpx import AsyncClient

BASE = "/api/v1"


# ── helpers ────────────────────────────────────────────────────────────────────

async def _auth(http_client: AsyncClient, email: str) -> dict:
    await http_client.post(f"{BASE}/auth/register", json={"email": email, "password": "StrongPass123!"})
    r = await http_client.post(f"{BASE}/auth/login", json={"email": email, "password": "StrongPass123!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

async def _auth_consultant(http_client, email: str) -> dict:
    """Register, login, and promote user to RSSI consultant for tests."""
    import app.core.database as _db_mod
    from sqlalchemy import select
    from app.models.user import User
    headers = await _auth(http_client, email)
    async with _db_mod.AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_rssi_consultant = True
        await db.commit()
    return headers




async def _create_client(http_client: AsyncClient, headers: dict, name: str = "Acme", **kwargs) -> dict:
    r = await http_client.post(f"{BASE}/rssi/clients", json={"name": name, **kwargs}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_action(http_client: AsyncClient, headers: dict, client_id: int, **kwargs) -> dict:
    payload = {"title": "Test action", "priority": "medium", **kwargs}
    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/actions", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


async def _create_visit(http_client: AsyncClient, headers: dict, client_id: int, scheduled_date: str, **kwargs) -> dict:
    payload = {"scheduled_date": scheduled_date, "visit_type": "monthly", "location": "onsite", **kwargs}
    r = await http_client.post(f"{BASE}/rssi/clients/{client_id}/visits", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Auth guards ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_overview_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/dashboard/overview")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_clients_summary_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/dashboard/clients-summary")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_alerts_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_events_requires_auth(http_client: AsyncClient):
    r = await http_client.get(f"{BASE}/rssi/dashboard/upcoming-events")
    assert r.status_code == 401


# ── Overview ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_overview_empty_returns_zeros(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_ov1@test.com")
    r = await http_client.get(f"{BASE}/rssi/dashboard/overview", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert body["total_clients"] == 0
    assert body["total_mrr"] == 0
    assert body["open_actions"] == 0
    assert body["overdue_actions"] == 0
    assert body["renewals_upcoming"] == 0
    assert body["upcoming_visits"] == 0


@pytest.mark.asyncio
async def test_overview_counts_active_clients_and_mrr(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_ov2@test.com")
    await _create_client(http_client, h, "Client A", monthly_amount=2000, formula="premium")
    await _create_client(http_client, h, "Client B", monthly_amount=1500, formula="essentiel")
    c_churned = await _create_client(http_client, h, "Client C", monthly_amount=3000)
    # Mark one as churned — should not count
    await http_client.put(f"{BASE}/rssi/clients/{c_churned['id']}", json={"status": "churned"}, headers=h)

    r = await http_client.get(f"{BASE}/rssi/dashboard/overview", headers=h)
    body = r.json()
    assert body["total_clients"] == 2
    assert body["total_mrr"] == 3500.0


@pytest.mark.asyncio
async def test_overview_counts_open_and_overdue_actions(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_ov3@test.com")
    c = await _create_client(http_client, h, "Corp")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    next_week = (date.today() + timedelta(days=7)).isoformat()

    await _create_action(http_client, h, c["id"], due_date=yesterday)   # overdue
    await _create_action(http_client, h, c["id"], due_date=next_week)    # open, not overdue
    await _create_action(http_client, h, c["id"])                        # open, no due_date

    r = await http_client.get(f"{BASE}/rssi/dashboard/overview", headers=h)
    body = r.json()
    assert body["open_actions"] == 3
    assert body["overdue_actions"] == 1


@pytest.mark.asyncio
async def test_overview_renewal_upcoming(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_ov4@test.com")
    soon = (date.today() + timedelta(days=30)).isoformat()
    far = (date.today() + timedelta(days=120)).isoformat()

    await _create_client(http_client, h, "Renew Soon", contract_renewal_at=soon)
    await _create_client(http_client, h, "Far Renewal", contract_renewal_at=far)

    r = await http_client.get(f"{BASE}/rssi/dashboard/overview", headers=h)
    assert r.json()["renewals_upcoming"] == 1


# ── Clients summary ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clients_summary_returns_all_clients(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_cs1@test.com")
    await _create_client(http_client, h, "Alpha")
    await _create_client(http_client, h, "Beta")

    r = await http_client.get(f"{BASE}/rssi/dashboard/clients-summary", headers=h)
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert "Alpha" in names
    assert "Beta" in names


@pytest.mark.asyncio
async def test_clients_summary_includes_action_counts(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_cs2@test.com")
    c = await _create_client(http_client, h, "ActionCorp")
    overdue_date = (date.today() - timedelta(days=5)).isoformat()
    await _create_action(http_client, h, c["id"], due_date=overdue_date)
    await _create_action(http_client, h, c["id"])

    r = await http_client.get(f"{BASE}/rssi/dashboard/clients-summary", headers=h)
    summary = next(s for s in r.json() if s["name"] == "ActionCorp")
    assert summary["open_actions"] == 2
    assert summary["overdue_actions"] == 1


@pytest.mark.asyncio
async def test_clients_summary_includes_next_visit(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_cs3@test.com")
    c = await _create_client(http_client, h, "VisitCorp")
    future = (date.today() + timedelta(days=10)).isoformat()
    await _create_visit(http_client, h, c["id"], future)

    r = await http_client.get(f"{BASE}/rssi/dashboard/clients-summary", headers=h)
    summary = next(s for s in r.json() if s["name"] == "VisitCorp")
    assert summary["next_visit"] == future


# ── Alerts ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_alerts_empty_when_no_issues(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_al1@test.com")
    c = await _create_client(http_client, h, "Healthy Corp")
    # Action with future due date — no overdue
    await _create_action(http_client, h, c["id"], due_date=(date.today() + timedelta(days=30)).isoformat())

    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts", headers=h)
    assert r.status_code == 200
    overdue_alerts = [a for a in r.json() if a["type"] == "overdue_action"]
    assert len(overdue_alerts) == 0


@pytest.mark.asyncio
async def test_alerts_detects_overdue_actions(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_al2@test.com")
    c = await _create_client(http_client, h, "Overdue Corp")
    overdue = (date.today() - timedelta(days=10)).isoformat()
    await _create_action(http_client, h, c["id"], title="Fix SSL", due_date=overdue)

    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts", headers=h)
    overdue_alerts = [a for a in r.json() if a["type"] == "overdue_action"]
    assert len(overdue_alerts) >= 1
    assert overdue_alerts[0]["client_name"] == "Overdue Corp"


@pytest.mark.asyncio
async def test_alerts_detects_renewal_upcoming(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_al3@test.com")
    soon = (date.today() + timedelta(days=20)).isoformat()
    await _create_client(http_client, h, "Renew Corp", contract_renewal_at=soon)

    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts", headers=h)
    renewal_alerts = [a for a in r.json() if a["type"] == "renewal_upcoming"]
    assert len(renewal_alerts) == 1


# ── Upcoming events ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upcoming_events_returns_planned_visits(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_ev1@test.com")
    c = await _create_client(http_client, h, "Event Corp")
    future = (date.today() + timedelta(days=7)).isoformat()
    await _create_visit(http_client, h, c["id"], future)

    r = await http_client.get(f"{BASE}/rssi/dashboard/upcoming-events", headers=h)
    assert r.status_code == 200
    events = r.json()
    assert len(events) == 1
    assert events[0]["client_name"] == "Event Corp"
    assert events[0]["scheduled_date"] == future


@pytest.mark.asyncio
async def test_upcoming_events_excludes_past_and_distant(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_ev2@test.com")
    c = await _create_client(http_client, h, "Corp2")

    past = (date.today() - timedelta(days=1)).isoformat()
    far = (date.today() + timedelta(days=30)).isoformat()
    soon = (date.today() + timedelta(days=5)).isoformat()

    await _create_visit(http_client, h, c["id"], past)
    await _create_visit(http_client, h, c["id"], far)
    await _create_visit(http_client, h, c["id"], soon)

    r = await http_client.get(f"{BASE}/rssi/dashboard/upcoming-events?days_ahead=14", headers=h)
    events = r.json()
    dates = [e["scheduled_date"] for e in events]
    assert soon in dates
    assert past not in dates
    assert far not in dates


# ── Suggestions ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_suggestions_empty_for_new_user(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_sg1@test.com")
    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_suggestions_high_overdue_rule(http_client: AsyncClient):
    h = await _auth_consultant(http_client, "dash_sg2@test.com")
    c = await _create_client(http_client, h, "Overdue Heavy")
    overdue = (date.today() - timedelta(days=5)).isoformat()
    for _ in range(3):
        await _create_action(http_client, h, c["id"], due_date=overdue)

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    high_overdue = [s for s in r.json() if s["type"] == "high_overdue"]
    assert len(high_overdue) == 1
    assert high_overdue[0]["client_name"] == "Overdue Heavy"


@pytest.mark.asyncio
async def test_suggestions_isolation_between_users(http_client: AsyncClient):
    """User B should not see suggestions for user A's clients."""
    h_a = await _auth_consultant(http_client, "dash_sg3a@test.com")
    h_b = await _auth_consultant(http_client, "dash_sg3b@test.com")

    c_a = await _create_client(http_client, h_a, "A Corp", formula="premium")
    overdue = (date.today() - timedelta(days=5)).isoformat()
    for _ in range(3):
        await _create_action(http_client, h_a, c_a["id"], due_date=overdue)

    r_b = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h_b)
    assert r_b.status_code == 200
    assert r_b.json() == []


# ── Coverage gaps: branches not yet covered ───────────────────────────────────

@pytest.mark.asyncio
async def test_upcoming_events_empty_when_no_clients(http_client: AsyncClient):
    """get_upcoming_events early-exit branch: user with no active clients."""
    h = await _auth_consultant(http_client, "dash_ev3@test.com")
    r = await http_client.get(f"{BASE}/rssi/dashboard/upcoming-events", headers=h)
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_alerts_no_recent_visit_for_premium_client(http_client: AsyncClient):
    """Premium client with no completed visit → no_recent_visit alert."""
    h = await _auth_consultant(http_client, "dash_al4@test.com")
    await _create_client(http_client, h, "Premium No Visit", formula="premium")

    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts", headers=h)
    no_visit_alerts = [a for a in r.json() if a["type"] == "no_recent_visit"]
    assert len(no_visit_alerts) == 1
    assert no_visit_alerts[0]["client_name"] == "Premium No Visit"


@pytest.mark.asyncio
async def test_alerts_no_recent_visit_premium_old_visit(http_client: AsyncClient):
    """Premium client whose last completed visit was >35 days ago → alert."""
    h = await _auth_consultant(http_client, "dash_al5@test.com")
    c = await _create_client(http_client, h, "Old Visit Corp", formula="excellence")

    # Create a visit in the past (>35 days) and mark it completed
    old_date = (date.today() - timedelta(days=40)).isoformat()
    v = await _create_visit(http_client, h, c["id"], old_date)
    await http_client.put(
        f"{BASE}/rssi/clients/{c['id']}/visits/{v['id']}",
        json={"status": "completed", "actual_date": old_date},
        headers=h,
    )

    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts", headers=h)
    no_visit_alerts = [a for a in r.json() if a["type"] == "no_recent_visit"]
    assert len(no_visit_alerts) == 1


@pytest.mark.asyncio
async def test_alerts_no_recent_visit_essentiel_client_ignored(http_client: AsyncClient):
    """Essentiel clients are NOT checked for visit frequency."""
    h = await _auth_consultant(http_client, "dash_al6@test.com")
    await _create_client(http_client, h, "Essentiel Corp", formula="essentiel")

    r = await http_client.get(f"{BASE}/rssi/dashboard/alerts", headers=h)
    no_visit_alerts = [a for a in r.json() if a["type"] == "no_recent_visit"]
    assert len(no_visit_alerts) == 0


@pytest.mark.asyncio
async def test_suggestions_upsell_opportunity(http_client: AsyncClient):
    """Essentiel client with 180+ days contract and zero overdue → upsell suggestion."""
    h = await _auth_consultant(http_client, "dash_sg4@test.com")
    old_start = (date.today() - timedelta(days=200)).isoformat()
    await _create_client(http_client, h, "Stable Essentiel", formula="essentiel",
                         contract_start_date=old_start)

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    upsell = [s for s in r.json() if s["type"] == "upsell_opportunity"]
    assert len(upsell) == 1
    assert upsell[0]["client_name"] == "Stable Essentiel"


@pytest.mark.asyncio
async def test_suggestions_no_upsell_when_overdue(http_client: AsyncClient):
    """Upsell rule must NOT fire when the client has overdue actions."""
    h = await _auth_consultant(http_client, "dash_sg5@test.com")
    old_start = (date.today() - timedelta(days=200)).isoformat()
    c = await _create_client(http_client, h, "Busy Essentiel", formula="essentiel",
                             contract_start_date=old_start)
    overdue = (date.today() - timedelta(days=5)).isoformat()
    await _create_action(http_client, h, c["id"], due_date=overdue)

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    upsell = [s for s in r.json() if s["type"] == "upsell_opportunity"]
    assert len(upsell) == 0


@pytest.mark.asyncio
async def test_suggestions_engagement_alert_for_premium_no_visit(http_client: AsyncClient):
    """Premium client with no visits at all → engagement_alert suggestion."""
    h = await _auth_consultant(http_client, "dash_sg6@test.com")
    await _create_client(http_client, h, "Ghosted Premium", formula="premium")

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    engagement = [s for s in r.json() if s["type"] == "engagement_alert"]
    assert len(engagement) == 1
    assert engagement[0]["client_name"] == "Ghosted Premium"
    assert engagement[0]["cta"] == "Planifier une visite"


@pytest.mark.asyncio
async def test_suggestions_renewal_30_to_60_days(http_client: AsyncClient):
    """Client with renewal in 30-60 days → renewal_upcoming suggestion."""
    h = await _auth_consultant(http_client, "dash_sg7@test.com")
    renewal = (date.today() + timedelta(days=45)).isoformat()
    await _create_client(http_client, h, "Renew Me", contract_renewal_at=renewal)

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    renew = [s for s in r.json() if s["type"] == "renewal_upcoming"]
    assert len(renew) == 1
    assert renew[0]["client_name"] == "Renew Me"


@pytest.mark.asyncio
async def test_suggestions_no_renewal_outside_window(http_client: AsyncClient):
    """Renewal outside 30-60 day window → no renewal_upcoming suggestion."""
    h = await _auth_consultant(http_client, "dash_sg8@test.com")
    far = (date.today() + timedelta(days=90)).isoformat()
    await _create_client(http_client, h, "Far Future", contract_renewal_at=far)

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    renew = [s for s in r.json() if s["type"] == "renewal_upcoming"]
    assert len(renew) == 0


@pytest.mark.asyncio
async def test_suggestions_no_engagement_alert_when_recent_visit(http_client: AsyncClient):
    """Premium client with a recent completed visit (< 35 days) → no engagement_alert."""
    h = await _auth_consultant(http_client, "dash_sg9@test.com")
    c = await _create_client(http_client, h, "Active Premium", formula="premium")

    recent = (date.today() - timedelta(days=10)).isoformat()
    v = await _create_visit(http_client, h, c["id"], recent)
    # Mark the visit as completed with an actual_date
    await http_client.put(
        f"{BASE}/rssi/clients/{c['id']}/visits/{v['id']}",
        json={"status": "completed", "actual_date": recent},
        headers=h,
    )

    r = await http_client.get(f"{BASE}/rssi/dashboard/suggestions", headers=h)
    engagement = [s for s in r.json() if s["type"] == "engagement_alert"]
    assert len(engagement) == 0
