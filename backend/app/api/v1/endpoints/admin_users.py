from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin/users", tags=["admin"])


@router.get("", dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User, Subscription, Plan)
        .outerjoin(
            Subscription,
            (Subscription.user_id == User.id) & (Subscription.status == "active"),
        )
        .outerjoin(Plan, Plan.id == Subscription.plan_id)
        .order_by(User.id.desc())
    )
    rows = result.all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "is_active": u.is_active,
            "is_rssi_consultant": u.is_rssi_consultant,
            "plan": p.display_name if p else "Gratuit",
            "plan_name": p.name if p else None,
            "subscription_status": s.status if s else None,
            "subscription_since": s.created_at.isoformat() if s else None,
        }
        for u, s, p in rows
    ]


@router.patch("/{user_id}/rssi", dependencies=[Depends(require_admin)])
async def toggle_rssi_consultant(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    user.is_rssi_consultant = not user.is_rssi_consultant
    await db.commit()
    return {"id": user.id, "is_rssi_consultant": user.is_rssi_consultant}
