"""RSSI aggregation service — Sprint 2.

Computes cross-client statistics and events for the consultant dashboard.
All queries scope by consultant_user_id to enforce client isolation.
"""
from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_action import RssiAction
from app.models.rssi_client import RssiClient
from app.models.rssi_visit import RssiVisit


# ── DTOs ──────────────────────────────────────────────────────────────────────

class DashboardOverview:
    def __init__(
        self,
        total_clients: int,
        total_mrr: float,
        open_actions: int,
        overdue_actions: int,
        renewals_upcoming: int,
        upcoming_visits: int,
    ):
        self.total_clients = total_clients
        self.total_mrr = total_mrr
        self.open_actions = open_actions
        self.overdue_actions = overdue_actions
        self.renewals_upcoming = renewals_upcoming
        self.upcoming_visits = upcoming_visits

    def dict(self):
        return {
            "total_clients": self.total_clients,
            "total_mrr": self.total_mrr,
            "open_actions": self.open_actions,
            "overdue_actions": self.overdue_actions,
            "renewals_upcoming": self.renewals_upcoming,
            "upcoming_visits": self.upcoming_visits,
        }


async def compute_overview(consultant_id: int, db: AsyncSession) -> DashboardOverview:
    """Aggregate dashboard stats across all active clients of a consultant."""
    today = date.today()
    renewal_horizon = today + timedelta(days=60)
    visit_horizon = today + timedelta(days=14)

    # Active clients
    clients_result = await db.execute(
        select(RssiClient).where(
            RssiClient.consultant_user_id == consultant_id,
            RssiClient.status == "active",
        )
    )
    clients = clients_result.scalars().all()
    client_ids = [c.id for c in clients]

    total_mrr = sum(float(c.monthly_amount or 0) for c in clients)
    renewals_upcoming = sum(
        1 for c in clients
        if c.contract_renewal_at and today <= c.contract_renewal_at <= renewal_horizon
    )

    open_actions = 0
    overdue_actions = 0
    upcoming_visits = 0

    if client_ids:
        actions_result = await db.execute(
            select(RssiAction).where(
                RssiAction.client_id.in_(client_ids),
                RssiAction.status.in_(["open", "in_progress"]),
            )
        )
        actions = actions_result.scalars().all()
        open_actions = len(actions)
        overdue_actions = sum(1 for a in actions if a.due_date and a.due_date < today)

        visits_result = await db.execute(
            select(RssiVisit).where(
                RssiVisit.client_id.in_(client_ids),
                RssiVisit.status == "planned",
                RssiVisit.scheduled_date >= today,
                RssiVisit.scheduled_date <= visit_horizon,
            )
        )
        upcoming_visits = len(visits_result.scalars().all())

    return DashboardOverview(
        total_clients=len(clients),
        total_mrr=total_mrr,
        open_actions=open_actions,
        overdue_actions=overdue_actions,
        renewals_upcoming=renewals_upcoming,
        upcoming_visits=upcoming_visits,
    )


async def get_clients_summary(consultant_id: int, db: AsyncSession) -> list[dict]:
    """Per-client summary: actions, overdue, next visit."""
    today = date.today()

    clients_result = await db.execute(
        select(RssiClient)
        .where(RssiClient.consultant_user_id == consultant_id)
        .order_by(RssiClient.created_at.desc())
    )
    clients = clients_result.scalars().all()
    client_ids = [c.id for c in clients]

    # Fetch all relevant actions and visits in bulk (avoid N+1)
    open_actions_by_client: dict[int, int] = {c.id: 0 for c in clients}
    overdue_by_client: dict[int, int] = {c.id: 0 for c in clients}
    next_visit_by_client: dict[int, str | None] = {c.id: None for c in clients}

    if client_ids:
        actions_result = await db.execute(
            select(RssiAction).where(
                RssiAction.client_id.in_(client_ids),
                RssiAction.status.in_(["open", "in_progress"]),
            )
        )
        for a in actions_result.scalars().all():
            open_actions_by_client[a.client_id] = open_actions_by_client.get(a.client_id, 0) + 1
            if a.due_date and a.due_date < today:
                overdue_by_client[a.client_id] = overdue_by_client.get(a.client_id, 0) + 1

        visits_result = await db.execute(
            select(RssiVisit).where(
                RssiVisit.client_id.in_(client_ids),
                RssiVisit.status == "planned",
                RssiVisit.scheduled_date >= today,
            ).order_by(RssiVisit.scheduled_date.asc())
        )
        for v in visits_result.scalars().all():
            if next_visit_by_client[v.client_id] is None:
                next_visit_by_client[v.client_id] = v.scheduled_date.isoformat()

    return [
        {
            "id": c.id,
            "name": c.name,
            "formula": c.formula,
            "monthly_amount": float(c.monthly_amount) if c.monthly_amount is not None else None,
            "status": c.status,
            "contract_renewal_at": c.contract_renewal_at.isoformat() if c.contract_renewal_at else None,
            "open_actions": open_actions_by_client.get(c.id, 0),
            "overdue_actions": overdue_by_client.get(c.id, 0),
            "next_visit": next_visit_by_client.get(c.id),
        }
        for c in clients
    ]


async def get_pending_alerts(consultant_id: int, db: AsyncSession) -> list[dict]:
    """
    Returns alerts that require the consultant's attention:
    - Overdue actions per client
    - Contracts renewing in the next 60 days
    - Premium/Excellence clients not visited in 35+ days
    """
    today = date.today()
    renewal_horizon = today + timedelta(days=60)
    visit_horizon = today - timedelta(days=35)

    clients_result = await db.execute(
        select(RssiClient).where(
            RssiClient.consultant_user_id == consultant_id,
            RssiClient.status == "active",
        )
    )
    clients = {c.id: c for c in clients_result.scalars().all()}
    client_ids = list(clients.keys())
    alerts = []

    if client_ids:
        # Overdue actions
        overdue_result = await db.execute(
            select(RssiAction).where(
                RssiAction.client_id.in_(client_ids),
                RssiAction.status.in_(["open", "in_progress"]),
                RssiAction.due_date < today,
            ).order_by(RssiAction.due_date.asc())
        )
        for a in overdue_result.scalars().all():
            c = clients[a.client_id]
            alerts.append({
                "type": "overdue_action",
                "severity": "high" if a.priority in ("critical", "high") else "medium",
                "client_id": c.id,
                "client_name": c.name,
                "title": f"{c.name} : action en retard — {a.title}",
                "detail": f"Échéance dépassée : {a.due_date.isoformat() if a.due_date else '?'}",
            })

    # Renewals upcoming (60 days)
    for c in clients.values():
        if c.contract_renewal_at and today <= c.contract_renewal_at <= renewal_horizon:
            days = (c.contract_renewal_at - today).days
            alerts.append({
                "type": "renewal_upcoming",
                "severity": "medium" if days > 30 else "high",
                "client_id": c.id,
                "client_name": c.name,
                "title": f"{c.name} : renouvellement dans {days} jour(s)",
                "detail": c.contract_renewal_at.isoformat(),
            })

    # No recent visit for Premium/Excellence clients
    if client_ids:
        premium_ids = [
            cid for cid, c in clients.items()
            if c.formula in ("premium", "excellence")
        ]
        if premium_ids:
            last_visits: dict[int, date] = {}
            visits_result = await db.execute(
                select(RssiVisit).where(
                    RssiVisit.client_id.in_(premium_ids),
                    RssiVisit.status == "completed",
                ).order_by(RssiVisit.actual_date.desc())
            )
            for v in visits_result.scalars().all():
                if v.client_id not in last_visits and v.actual_date:
                    last_visits[v.client_id] = v.actual_date

            for cid in premium_ids:
                last = last_visits.get(cid)
                if last is None or last < visit_horizon:
                    days_ago = (today - last).days if last else None
                    c = clients[cid]
                    detail = f"Dernière visite il y a {days_ago} jour(s)" if days_ago else "Aucune visite enregistrée"
                    alerts.append({
                        "type": "no_recent_visit",
                        "severity": "medium",
                        "client_id": c.id,
                        "client_name": c.name,
                        "title": f"{c.name} : pas de visite récente",
                        "detail": detail,
                    })

    return alerts


async def get_upcoming_events(consultant_id: int, days_ahead: int, db: AsyncSession) -> list[dict]:
    """Planned visits within the next `days_ahead` days."""
    today = date.today()
    horizon = today + timedelta(days=days_ahead)

    clients_result = await db.execute(
        select(RssiClient).where(
            RssiClient.consultant_user_id == consultant_id,
            RssiClient.status == "active",
        )
    )
    clients = {c.id: c for c in clients_result.scalars().all()}
    client_ids = list(clients.keys())

    if not client_ids:
        return []

    visits_result = await db.execute(
        select(RssiVisit).where(
            RssiVisit.client_id.in_(client_ids),
            RssiVisit.status == "planned",
            RssiVisit.scheduled_date >= today,
            RssiVisit.scheduled_date <= horizon,
        ).order_by(RssiVisit.scheduled_date.asc())
    )

    return [
        {
            "visit_id": v.id,
            "client_id": v.client_id,
            "client_name": clients[v.client_id].name,
            "scheduled_date": v.scheduled_date.isoformat(),
            "visit_type": v.visit_type,
            "location": v.location,
        }
        for v in visits_result.scalars().all()
        if v.client_id in clients
    ]


async def compute_suggestions(consultant_id: int, db: AsyncSession) -> list[dict]:
    """
    Rule-based suggestions:
    1. Upsell: essentiel client, stable 6+ months → upgrade to premium
    2. Engagement alert: premium/excellence, not visited in 35+ days
    3. Renewal: contract renewing in 30-60 days
    4. High overdue: 3+ overdue actions
    """
    today = date.today()

    clients_result = await db.execute(
        select(RssiClient).where(
            RssiClient.consultant_user_id == consultant_id,
            RssiClient.status == "active",
        )
    )
    clients = clients_result.scalars().all()
    client_ids = [c.id for c in clients]
    suggestions = []

    if not client_ids:
        return suggestions

    # Fetch overdue counts per client
    overdue_result = await db.execute(
        select(RssiAction).where(
            RssiAction.client_id.in_(client_ids),
            RssiAction.status.in_(["open", "in_progress"]),
            RssiAction.due_date < today,
        )
    )
    overdue_by_client: dict[int, int] = {}
    for a in overdue_result.scalars().all():
        overdue_by_client[a.client_id] = overdue_by_client.get(a.client_id, 0) + 1

    # Last completed visit per client
    visits_result = await db.execute(
        select(RssiVisit).where(
            RssiVisit.client_id.in_(client_ids),
            RssiVisit.status == "completed",
        ).order_by(RssiVisit.actual_date.desc())
    )
    last_visit: dict[int, date] = {}
    for v in visits_result.scalars().all():
        if v.client_id not in last_visit and v.actual_date:
            last_visit[v.client_id] = v.actual_date

    for c in clients:
        overdue_count = overdue_by_client.get(c.id, 0)
        last = last_visit.get(c.id)

        # Rule 1 — Upsell: essentiel client stable > 6 months with no overdue actions
        if (
            c.formula == "essentiel"
            and c.contract_start_date
            and (today - c.contract_start_date).days > 180
            and overdue_count == 0
        ):
            suggestions.append({
                "type": "upsell_opportunity",
                "client_id": c.id,
                "client_name": c.name,
                "title": f"{c.name} : opportunité upsell Premium",
                "reason": "Client stable depuis plus de 6 mois, sans action en retard.",
                "cta": "Proposer un upgrade",
            })

        # Rule 2 — Engagement alert: premium/excellence not visited in 35+ days
        if c.formula in ("premium", "excellence"):
            days_ago = (today - last).days if last else None
            if last is None or (today - last).days > 35:
                label = f"depuis {days_ago} jour(s)" if days_ago else "jamais"
                suggestions.append({
                    "type": "engagement_alert",
                    "client_id": c.id,
                    "client_name": c.name,
                    "title": f"{c.name} : pas de visite {label}",
                    "reason": "Risque de désengagement client.",
                    "cta": "Planifier une visite",
                })

        # Rule 3 — Renewal 30-60 days
        if c.contract_renewal_at:
            days_to_renewal = (c.contract_renewal_at - today).days
            if 30 <= days_to_renewal <= 60:
                suggestions.append({
                    "type": "renewal_upcoming",
                    "client_id": c.id,
                    "client_name": c.name,
                    "title": f"{c.name} : renouvellement dans {days_to_renewal} jour(s)",
                    "reason": "Préparer le bilan et proposer l'évolution du contrat.",
                    "cta": "Préparer le bilan annuel",
                })

        # Rule 4 — High overdue count
        if overdue_count >= 3:
            suggestions.append({
                "type": "high_overdue",
                "client_id": c.id,
                "client_name": c.name,
                "title": f"{c.name} : {overdue_count} actions en retard",
                "reason": "Plan d'action à réviser en urgence.",
                "cta": "Voir le plan d'action",
            })

    return suggestions
