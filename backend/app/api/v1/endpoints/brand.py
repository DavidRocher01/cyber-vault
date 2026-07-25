from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services import brand_service

router = APIRouter(prefix="/brand", tags=["brand"])


class BrandProfileOut(BaseModel):
    company_name: str
    accent_color: str
    logo_b64: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}


class BrandProfileIn(BaseModel):
    company_name: str = Field(..., min_length=1, max_length=255)
    accent_color: str = Field(default="#06b6d4", pattern=r"^#[0-9a-fA-F]{6}$")
    logo_b64: str | None = None


@router.get("/me", response_model=BrandProfileOut | None)
async def get_brand(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await brand_service.get_brand_profile(db, current_user.id)


@router.put("/me", response_model=BrandProfileOut)
async def upsert_brand(
    payload: BrandProfileIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await brand_service.upsert_brand_profile(
        db,
        current_user.id,
        company_name=payload.company_name,
        accent_color=payload.accent_color,
        logo_b64=payload.logo_b64,
    )
