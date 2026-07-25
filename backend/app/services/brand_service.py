"""Service du profil de marque (white-label) d'un utilisateur."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_profile import BrandProfile


async def get_brand_profile(db: AsyncSession, user_id: int) -> BrandProfile | None:
    """Retourne le profil de marque de l'utilisateur, sinon None."""
    result = await db.execute(select(BrandProfile).where(BrandProfile.user_id == user_id))
    return result.scalar_one_or_none()


async def upsert_brand_profile(
    db: AsyncSession,
    user_id: int,
    *,
    company_name: str,
    accent_color: str,
    logo_b64: str | None,
) -> BrandProfile:
    """Crée ou met à jour le profil de marque de l'utilisateur."""
    brand = await get_brand_profile(db, user_id)
    if brand is None:
        brand = BrandProfile(user_id=user_id)
        db.add(brand)

    brand.company_name = company_name
    brand.accent_color = accent_color
    brand.logo_b64 = logo_b64
    brand.updated_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(brand)
    return brand
