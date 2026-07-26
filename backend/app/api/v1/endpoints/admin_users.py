from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_admin
from app.services import plan_service, subscription_service, user_admin_service

router = APIRouter(prefix="/admin/users", tags=["admin"])


class SetPlanIn(BaseModel):
    """Corps de la requête d'attribution manuelle d'un plan (override admin)."""

    model_config = ConfigDict(extra="forbid")

    plan_name: str = Field(min_length=1, description="Nom technique du plan (ex. 'starter')")


@router.get(
    "",
    dependencies=[Depends(require_admin)],
    summary="[Admin] Lister les utilisateurs (paginé)",
)
async def list_users(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    rows = await user_admin_service.list_users_with_plan(db, skip=skip, limit=limit)
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


@router.patch(
    "/{user_id}/rssi",
    dependencies=[Depends(require_admin)],
    summary="[Admin] Activer/désactiver le rôle consultant RSSI",
)
async def toggle_rssi_consultant(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await user_admin_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    user = await user_admin_service.toggle_rssi_consultant(db, user)
    return {"id": user.id, "is_rssi_consultant": user.is_rssi_consultant}


@router.patch(
    "/{user_id}/plan",
    dependencies=[Depends(require_admin)],
    summary="[Admin] Attribuer/rétrograder le plan d'un utilisateur (sans Stripe)",
)
async def set_user_plan(user_id: int, payload: SetPlanIn, db: AsyncSession = Depends(get_db)):
    """Attribue un plan à un utilisateur SANS passer par Stripe (piste A).

    Sert à tester les quotas/export/scan d'un palier ou à offrir un plan à un client.
    Ne facture rien : la facturation réelle (proration, webhooks) passe toujours par
    le checkout Stripe.
    """
    user = await user_admin_service.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    plan = await plan_service.get_plan_by_name(db, payload.plan_name)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan introuvable")
    await subscription_service.admin_set_user_plan(
        db, user_id=user.id, plan=plan, now=datetime.now(UTC)
    )
    return {
        "id": user.id,
        "plan": plan.display_name,
        "plan_name": plan.name,
        "max_sites": plan.max_sites,
        "scan_interval_days": plan.scan_interval_days,
        "allow_conformity_export": plan.allow_conformity_export,
    }
