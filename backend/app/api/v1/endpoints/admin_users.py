import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.plan import Plan
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter(prefix="/admin/users", tags=["admin"])


def _require_admin(x_admin_key: str = Header(default="")) -> None:
    if not settings.ADMIN_API_KEY or not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")


@router.get("", dependencies=[Depends(_require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User, Subscription, Plan)
        .outerjoin(Subscription, (Subscription.user_id == User.id) & (Subscription.status == "active"))
        .outerjoin(Plan, Plan.id == Subscription.plan_id)
        .order_by(User.id.desc())
    )
    rows = result.all()
    return [
        {
            "id": u.id,
            "email": u.email,
            "is_active": u.is_active,
            "plan": p.display_name if p else "Gratuit",
            "plan_name": p.name if p else None,
            "subscription_status": s.status if s else None,
            "subscription_since": s.created_at.isoformat() if s else None,
        }
        for u, s, p in rows
    ]
