from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_action import RssiAction
from app.models.rssi_deliverable import RssiDeliverable
from app.models.rssi_visit import RssiVisit
from app.models.user import User
from ._shared import _get_client_or_404

router = APIRouter()


@router.get("/clients/{client_id}/report")
async def get_client_report(
    client_id: int,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Generate and stream a PDF report for a client."""
    from app.services.rssi_report_pdf import generate_rssi_report

    client = await _get_client_or_404(client_id, current_user.id, db)

    visits_result = await db.execute(
        select(RssiVisit)
        .where(RssiVisit.client_id == client_id)
        .order_by(RssiVisit.scheduled_date.desc())
    )
    actions_result = await db.execute(
        select(RssiAction)
        .where(RssiAction.client_id == client_id)
        .order_by(RssiAction.created_at.desc())
    )
    deliverables_result = await db.execute(
        select(RssiDeliverable)
        .where(RssiDeliverable.client_id == client_id)
        .order_by(RssiDeliverable.delivered_at.desc())
    )

    client_dict = {
        "name":                  client.name,
        "email":                 client.email,
        "description":           client.description,
        "formula":               client.formula,
        "monthly_amount":        float(client.monthly_amount) if client.monthly_amount else None,
        "contract_renewal_at":   str(client.contract_renewal_at) if client.contract_renewal_at else None,
        "status":                client.status,
        "notion_workspace_url":  client.notion_workspace_url,
        "pipedrive_deal_id":     client.pipedrive_deal_id,
        "pennylane_customer_id": client.pennylane_customer_id,
    }
    actions_list = [
        {
            "title":       a.title,
            "priority":    a.priority,
            "status":      a.status,
            "due_date":    str(a.due_date) if a.due_date else None,
            "assigned_to": a.assigned_to,
            "category":    a.category,
        }
        for a in actions_result.scalars().all()
    ]
    visits_list = [
        {
            "scheduled_date": str(v.scheduled_date),
            "visit_type":     v.visit_type,
            "location":       v.location,
            "status":         v.status,
            "duration_hours": float(v.duration_hours) if v.duration_hours else None,
            "actual_date":    str(v.actual_date) if v.actual_date else None,
        }
        for v in visits_result.scalars().all()
    ]
    deliverables_list = [
        {
            "title":        d.title,
            "doc_type":     d.doc_type,
            "delivered_at": str(d.delivered_at),
            "file_url":     d.file_url,
            "notes":        d.notes,
        }
        for d in deliverables_result.scalars().all()
    ]

    consultant_dict = {
        "email":        current_user.email,
        "display_name": current_user.display_name,
        "company_name": current_user.company_name,
        "phone":        current_user.phone,
    }
    pdf_bytes = generate_rssi_report(client_dict, actions_list, visits_list, deliverables_list, consultant_dict)
    safe_name = client.name.replace(" ", "_").replace("/", "-").lower()
    filename  = f"rapport_rssi_{safe_name}.pdf"

    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
