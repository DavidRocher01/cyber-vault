from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.limiter import limiter
from app.schemas.api_waitlist import ApiWaitlistIn, ApiWaitlistOut
from app.services import api_waitlist_service

router = APIRouter(prefix="/api-waitlist", tags=["api-waitlist"])


@router.post("", response_model=ApiWaitlistOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def join_waitlist(
    request: Request, data: ApiWaitlistIn, db: AsyncSession = Depends(get_db)
) -> ApiWaitlistOut:
    if await api_waitlist_service.get_by_email(db, data.email):
        raise HTTPException(
            status_code=409, detail="Vous êtes déjà inscrit(e) sur la liste d'attente."
        )

    await api_waitlist_service.add_entry(db, email=data.email, role=data.role, company=data.company)
    return ApiWaitlistOut(count=await api_waitlist_service.count_entries(db))


@router.get("/count", response_model=ApiWaitlistOut)
async def get_count(db: AsyncSession = Depends(get_db)) -> ApiWaitlistOut:
    return ApiWaitlistOut(count=await api_waitlist_service.count_entries(db))
