"""Service du profil consultant RSSI (mise à jour des coordonnées)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def update_consultant_profile(
    db: AsyncSession,
    user: User,
    *,
    display_name: str | None,
    company_name: str | None,
    phone: str | None,
) -> User:
    """Applique les champs fournis (non None), les trim, et persiste."""
    if display_name is not None:
        user.display_name = display_name.strip() or None
    if company_name is not None:
        user.company_name = company_name.strip() or None
    if phone is not None:
        user.phone = phone.strip() or None
    await db.commit()
    await db.refresh(user)
    return user
