import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.plan import Plan
from app.schemas.cyberscan import PlanOut

router = APIRouter(prefix="/plans", tags=["plans"])

# Cache TTL en mémoire : les plans changent très rarement (admin/migration), mais
# l'endpoint est public et appelé à chaque affichage du pricing. On met en cache la
# sortie *sérialisée* (objets PlanOut détachés de la session DB, donc réutilisables).
# Staleness max ~5 min, acceptable pour un affichage de prix. Cache par instance ;
# avec plusieurs instances chacune a le sien (sans incohérence, données read-only).
_CACHE_TTL_SECONDS = 300
_cache: dict[str, object] = {"data": None, "ts": 0.0}


def reset_plans_cache() -> None:
    """Vide le cache en mémoire — utilisé par les tests (évite la pollution croisée)."""
    _cache["data"] = None
    _cache["ts"] = 0.0


@router.get("", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db)):
    """Return all active subscription plans (cache mémoire ~5 min)."""
    now = time.monotonic()
    cached = _cache["data"]
    if cached is not None and now - float(_cache["ts"]) < _CACHE_TTL_SECONDS:
        return cached

    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.price_eur))  # noqa: E712
    plans = [PlanOut.model_validate(p) for p in result.scalars().all()]
    _cache["data"] = plans
    _cache["ts"] = now
    return plans
