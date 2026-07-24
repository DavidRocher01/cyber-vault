"""Service d'acces au coffre-fort (VaultItem) avec controle de propriete.

Le backend ne manipule que des blobs opaques : les champs sensibles sont chiffres
cote client (AES-GCM). Ce service ne fait qu'du CRUD filtre par proprietaire.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vault_item import VaultItem


async def list_items(db: AsyncSession, owner_id: int, *, skip: int, limit: int) -> list[VaultItem]:
    """Entrees du coffre appartenant a l'utilisateur (paginees)."""
    result = await db.execute(
        select(VaultItem).where(VaultItem.owner_id == owner_id).offset(skip).limit(limit)
    )
    return list(result.scalars().all())


async def get_item(db: AsyncSession, owner_id: int, item_id: int) -> VaultItem | None:
    """Entree du coffre par id si elle appartient a l'utilisateur, sinon None."""
    result = await db.execute(
        select(VaultItem).where(VaultItem.id == item_id, VaultItem.owner_id == owner_id)
    )
    return result.scalar_one_or_none()


async def create_item(db: AsyncSession, owner_id: int, values: dict) -> VaultItem:
    """Cree une entree de coffre pour l'utilisateur a partir de blobs opaques."""
    item = VaultItem(**values, owner_id=owner_id)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def save_item(db: AsyncSession, item: VaultItem) -> VaultItem:
    """Persiste les modifications d'une entree de coffre."""
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item: VaultItem) -> None:
    """Supprime une entree de coffre."""
    await db.delete(item)
    await db.commit()
