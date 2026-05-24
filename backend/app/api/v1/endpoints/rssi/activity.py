from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.rssi_activity_log import RssiActivityLog
from app.models.user import User
from ._shared import _get_client_or_404

router = APIRouter()

ActivityActionType = Literal[
    "view_client", "view_sites", "view_scans", "view_findings",
    "generate_report", "send_deliverable", "create_action", "update_action",
    "create_visit", "update_visit",
]


class ActivityLogCreate(BaseModel):
    action_type: ActivityActionType
    resource_type: str | None = None
    resource_id: int | None = None


class ActivityLogOut(BaseModel):
    id: int
    consultant_id: int
    client_id: int
    action_type: str
    resource_type: str | None
    resource_id: int | None
    performed_at: datetime

    model_config = {"from_attributes": True}


@router.post("/clients/{client_id}/activity", response_model=ActivityLogOut, status_code=201)
async def log_activity(
    client_id: int,
    body: ActivityLogCreate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """Record a consultant action on a client account."""
    await _get_client_or_404(client_id, current_user.id, db)

    entry = RssiActivityLog(
        consultant_id=current_user.id,
        client_id=client_id,
        action_type=body.action_type,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        performed_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/clients/{client_id}/activity", response_model=list[ActivityLogOut])
async def get_activity_log(
    client_id: int,
    limit: int = 50,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    """List the N most recent activity log entries for a client (default 50)."""
    await _get_client_or_404(client_id, current_user.id, db)

    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit doit être entre 1 et 200",
        )

    result = await db.execute(
        select(RssiActivityLog)
        .where(
            RssiActivityLog.client_id == client_id,
            RssiActivityLog.consultant_id == current_user.id,
        )
        .order_by(RssiActivityLog.performed_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
