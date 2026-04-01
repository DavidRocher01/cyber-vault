from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.models.user import User
from app.models.vault_item import VaultItem
from app.schemas.vault_item import VaultItemCreate, VaultItemOut, VaultItemUpdate

router = APIRouter(prefix="/vault", tags=["vault"])


@router.get("/", response_model=list[VaultItemOut])
@limiter.limit("60/minute")
async def list_items(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VaultItem)
        .where(VaultItem.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.post("/", response_model=VaultItemOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_item(
    request: Request,
    payload: VaultItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = VaultItem(**payload.model_dump(), owner_id=current_user.id)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.get("/{item_id}", response_model=VaultItemOut)
@limiter.limit("60/minute")
async def get_item(
    request: Request,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VaultItem).where(VaultItem.id == item_id, VaultItem.owner_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    return item


@router.patch("/{item_id}", response_model=VaultItemOut)
@limiter.limit("30/minute")
async def update_item(
    request: Request,
    item_id: int,
    payload: VaultItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VaultItem).where(VaultItem.id == item_id, VaultItem.owner_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_item(
    request: Request,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(VaultItem).where(VaultItem.id == item_id, VaultItem.owner_id == current_user.id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    await db.delete(item)
