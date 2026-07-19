from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.models.api_waitlist import ApiWaitlist
from app.schemas.api_waitlist import ApiWaitlistIn, ApiWaitlistOut

router = APIRouter(prefix="/api-waitlist", tags=["api-waitlist"])


@router.post("", response_model=ApiWaitlistOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def join_waitlist(
    request: Request, data: ApiWaitlistIn, db: AsyncSession = Depends(get_db)
) -> ApiWaitlistOut:
    existing = await db.execute(select(ApiWaitlist).where(ApiWaitlist.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail="Vous êtes déjà inscrit(e) sur la liste d'attente."
        )

    entry = ApiWaitlist(
        email=data.email,
        role=data.role,
        company=data.company,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    await db.commit()

    count_result = await db.execute(select(func.count(ApiWaitlist.id)))
    return ApiWaitlistOut(count=count_result.scalar() or 0)


@router.get("/count", response_model=ApiWaitlistOut)
async def get_count(db: AsyncSession = Depends(get_db)) -> ApiWaitlistOut:
    result = await db.execute(select(func.count(ApiWaitlist.id)))
    return ApiWaitlistOut(count=result.scalar() or 0)
