"""Portail client RSSI — vues LECTURE SEULE de la mission d'un client.

Toutes les routes dépendent de `get_current_rssi_client` : elles sont scopées au RssiClient
rattaché au compte connecté (client_user_id). Un client ne voit donc QUE ses propres données.
On n'expose volontairement pas les champs internes/CRM (consultant_user_id, pipedrive/pennylane/
notion, extra_data, file_url S3).
"""

from datetime import UTC, date, datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_rssi_client
from app.models.rssi_action import RssiAction
from app.models.rssi_client import RssiClient
from app.models.rssi_deliverable import RssiDeliverable
from app.models.rssi_visit import RssiVisit
from app.models.user import User

router = APIRouter(prefix="/portal", tags=["portal-client"])


# ── Schémas de sortie (champs sûrs uniquement) ────────────────────────────────


class ConsultantContact(BaseModel):
    display_name: str | None
    company_name: str | None
    email: str
    phone: str | None


class PortalActionOut(BaseModel):
    id: int
    title: str
    description: str | None
    category: str | None
    priority: str
    status: str
    assigned_to: str | None
    due_date: date | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class PortalVisitOut(BaseModel):
    id: int
    scheduled_date: date
    visit_type: str
    location: str | None
    status: str
    actual_date: date | None
    duration_hours: float | None

    model_config = {"from_attributes": True}


class PortalDeliverableOut(BaseModel):
    id: int
    title: str
    doc_type: str
    delivered_at: date
    notes: str | None
    has_file: bool


class PortalMeOut(BaseModel):
    name: str
    formula: str | None
    status: str
    contract_start_date: date | None
    contract_renewal_at: date | None
    consultant: ConsultantContact | None
    # Avancement de la mise en conformité (basé sur le plan d'action)
    progress_score: int
    actions_total: int
    actions_open: int
    actions_in_progress: int
    actions_done: int
    actions_overdue: int
    next_visit: PortalVisitOut | None


def _progress_score(actions: list[RssiAction]) -> int:
    """Score d'avancement 0-100 : done=2 pts, in_progress=1, open=0.
    Les actions annulées/reportées sont exclues du dénominateur."""
    considered = [a for a in actions if a.status in ("open", "in_progress", "done")]
    if not considered:
        return 0
    pts = sum(
        2 if a.status == "done" else 1 if a.status == "in_progress" else 0 for a in considered
    )
    return round(pts / (len(considered) * 2) * 100)


@router.get("/me", response_model=PortalMeOut)
async def get_my_mission(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    actions = (
        (await db.execute(select(RssiAction).where(RssiAction.client_id == client.id)))
        .scalars()
        .all()
    )
    today = datetime.now(UTC).date()
    overdue = sum(
        1
        for a in actions
        if a.status in ("open", "in_progress") and a.due_date and a.due_date < today
    )

    # Prochaine visite planifiée (à venir)
    next_visit = (
        await db.execute(
            select(RssiVisit)
            .where(
                RssiVisit.client_id == client.id,
                RssiVisit.status == "planned",
                RssiVisit.scheduled_date >= today,
            )
            .order_by(RssiVisit.scheduled_date.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    consultant = (
        await db.execute(select(User).where(User.id == client.consultant_user_id))
    ).scalar_one_or_none()

    return PortalMeOut(
        name=client.name,
        formula=client.formula,
        status=client.status,
        contract_start_date=client.contract_start_date,
        contract_renewal_at=client.contract_renewal_at,
        consultant=ConsultantContact(
            display_name=consultant.display_name,
            company_name=consultant.company_name,
            email=consultant.email,
            phone=consultant.phone,
        )
        if consultant
        else None,
        progress_score=_progress_score(list(actions)),
        actions_total=len(actions),
        actions_open=sum(1 for a in actions if a.status == "open"),
        actions_in_progress=sum(1 for a in actions if a.status == "in_progress"),
        actions_done=sum(1 for a in actions if a.status == "done"),
        actions_overdue=overdue,
        next_visit=PortalVisitOut.model_validate(next_visit) if next_visit else None,
    )


@router.get("/actions", response_model=list[PortalActionOut])
async def list_my_actions(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RssiAction)
        .where(RssiAction.client_id == client.id)
        .order_by(RssiAction.created_at.desc())
    )
    return result.scalars().all()


@router.get("/visits", response_model=list[PortalVisitOut])
async def list_my_visits(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client.id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    return result.scalars().all()


@router.get("/deliverables", response_model=list[PortalDeliverableOut])
async def list_my_deliverables(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client.id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )
    return [
        PortalDeliverableOut(
            id=d.id,
            title=d.title,
            doc_type=d.doc_type,
            delivered_at=d.delivered_at,
            notes=d.notes,
            has_file=bool(d.file_url),
        )
        for d in result.scalars().all()
    ]


@router.get("/deliverables/{deliverable_id}/download")
async def download_my_deliverable(
    deliverable_id: int,
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    from app.services.storage import get_download_url

    deliverable = (
        await db.execute(
            select(RssiDeliverable).where(
                RssiDeliverable.id == deliverable_id,
                RssiDeliverable.client_id == client.id,
            )
        )
    ).scalar_one_or_none()
    if deliverable is None:
        raise HTTPException(status_code=404, detail="Livrable non trouvé")
    if not deliverable.file_url:
        raise HTTPException(status_code=404, detail="Aucun fichier associé")
    return {"url": get_download_url(deliverable.file_url)}


@router.get("/report")
async def download_my_report(
    client: RssiClient = Depends(get_current_rssi_client),
    db: AsyncSession = Depends(get_db),
):
    """Rapport PDF de la mission (réutilise le générateur consultant)."""
    from app.services.rssi_report_pdf import generate_rssi_report

    actions = (
        (
            await db.execute(
                select(RssiAction)
                .where(RssiAction.client_id == client.id)
                .order_by(RssiAction.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    visits = (
        (
            await db.execute(
                select(RssiVisit)
                .where(RssiVisit.client_id == client.id)
                .order_by(RssiVisit.scheduled_date.desc())
            )
        )
        .scalars()
        .all()
    )
    deliverables = (
        (
            await db.execute(
                select(RssiDeliverable)
                .where(RssiDeliverable.client_id == client.id)
                .order_by(RssiDeliverable.delivered_at.desc())
            )
        )
        .scalars()
        .all()
    )
    consultant = (
        await db.execute(select(User).where(User.id == client.consultant_user_id))
    ).scalar_one_or_none()

    client_dict = {
        "name": client.name,
        "email": client.email,
        "description": client.description,
        "formula": client.formula,
        "monthly_amount": float(client.monthly_amount) if client.monthly_amount else None,
        "contract_renewal_at": str(client.contract_renewal_at)
        if client.contract_renewal_at
        else None,
        "status": client.status,
    }
    actions_list = [
        {
            "title": a.title,
            "priority": a.priority,
            "status": a.status,
            "due_date": str(a.due_date) if a.due_date else None,
            "assigned_to": a.assigned_to,
            "category": a.category,
        }
        for a in actions
    ]
    visits_list = [
        {
            "scheduled_date": str(v.scheduled_date),
            "visit_type": v.visit_type,
            "location": v.location,
            "status": v.status,
            "duration_hours": float(v.duration_hours) if v.duration_hours else None,
            "actual_date": str(v.actual_date) if v.actual_date else None,
        }
        for v in visits
    ]
    deliverables_list = [
        {
            "title": d.title,
            "doc_type": d.doc_type,
            "delivered_at": str(d.delivered_at),
            "file_url": d.file_url,
            "notes": d.notes,
        }
        for d in deliverables
    ]
    consultant_dict = {
        "email": consultant.email if consultant else "",
        "display_name": consultant.display_name if consultant else None,
        "company_name": consultant.company_name if consultant else None,
        "phone": consultant.phone if consultant else None,
    }
    pdf_bytes = generate_rssi_report(
        client_dict, actions_list, visits_list, deliverables_list, consultant_dict
    )
    safe_name = client.name.replace(" ", "_").replace("/", "-").lower()
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=rapport_rssi_{safe_name}.pdf"},
    )
