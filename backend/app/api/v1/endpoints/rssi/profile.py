from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_rssi_consultant
from app.models.user import User
from app.services import consultant_service

router = APIRouter()


class ConsultantProfileOut(BaseModel):
    email: str
    display_name: str | None
    company_name: str | None
    phone: str | None

    model_config = {"from_attributes": False}


class ConsultantProfileUpdate(BaseModel):
    display_name: str | None = None
    company_name: str | None = None
    phone: str | None = None


@router.get("/profile", response_model=ConsultantProfileOut)
async def get_consultant_profile(
    current_user: User = Depends(get_rssi_consultant),
):
    return ConsultantProfileOut(
        email=current_user.email,
        display_name=current_user.display_name,
        company_name=current_user.company_name,
        phone=current_user.phone,
    )


@router.patch("/profile", response_model=ConsultantProfileOut)
async def update_consultant_profile(
    payload: ConsultantProfileUpdate,
    current_user: User = Depends(get_rssi_consultant),
    db: AsyncSession = Depends(get_db),
):
    await consultant_service.update_consultant_profile(
        db,
        current_user,
        display_name=payload.display_name,
        company_name=payload.company_name,
        phone=payload.phone,
    )
    return ConsultantProfileOut(
        email=current_user.email,
        display_name=current_user.display_name,
        company_name=current_user.company_name,
        phone=current_user.phone,
    )
