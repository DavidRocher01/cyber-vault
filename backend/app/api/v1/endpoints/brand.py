from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.brand_profile import BrandProfile
from app.models.user import User

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
    result = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id))
    return result.scalar_one_or_none()


@router.put("/me", response_model=BrandProfileOut)
async def upsert_brand(
    payload: BrandProfileIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(BrandProfile).where(BrandProfile.user_id == current_user.id))
    brand = result.scalar_one_or_none()

    if brand is None:
        brand = BrandProfile(user_id=current_user.id)
        db.add(brand)

    brand.company_name = payload.company_name
    brand.accent_color = payload.accent_color
    brand.logo_b64 = payload.logo_b64
    brand.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(brand)
    return brand
