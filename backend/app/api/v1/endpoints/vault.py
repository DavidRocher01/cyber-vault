from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.models.user import User
from app.schemas.vault_item import VaultItemCreate, VaultItemOut, VaultItemUpdate
from app.services import vault_service

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
    return await vault_service.list_items(db, current_user.id, skip=skip, limit=limit)


@router.post("/", response_model=VaultItemOut, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_item(
    request: Request,
    payload: VaultItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await vault_service.create_item(db, current_user.id, payload.model_dump())


@router.get("/{item_id}", response_model=VaultItemOut)
@limiter.limit("60/minute")
async def get_item(
    request: Request,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await vault_service.get_item(db, current_user.id, item_id)
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
    item = await vault_service.get_item(db, current_user.id, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    return await vault_service.save_item(db, item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_item(
    request: Request,
    item_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await vault_service.get_item(db, current_user.id, item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée introuvable")
    await vault_service.delete_item(db, item)
