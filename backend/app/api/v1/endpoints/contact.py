from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import require_admin
from app.core.limiter import limiter
from app.models.contact_message import ContactMessage
from app.schemas.contact import ContactIn
from app.services.email_service import send_contact_email

router = APIRouter(prefix="/contact", tags=["contact"])


class ContactMessageOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    need_type: str
    site_url: str | None
    message: str
    status: str
    created_at: str

    model_config = {"from_attributes": True}


@router.post(
    "",
    status_code=status.HTTP_200_OK,
    summary="Envoyer un message de contact / demande de devis",
    responses={429: {"description": "Rate-limit (3/heure par IP)"}},
)
@limiter.limit("3/hour")
async def submit_contact(
    request: Request,
    payload: ContactIn,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    msg = ContactMessage(
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        need_type=payload.need_type,
        site_url=payload.site_url,
        message=payload.message,
        status="new",
        created_at=datetime.now(UTC),
    )
    db.add(msg)
    await db.commit()
    background_tasks.add_task(
        send_contact_email,
        name=payload.name,
        email=str(payload.email),
        phone=payload.phone,
        need_type=payload.need_type,
        site_url=payload.site_url,
        message=payload.message,
        contact_email=settings.CONTACT_EMAIL,
    )
    return {"message": "Votre message a bien été envoyé. Je vous répondrai sous 4 h."}


@router.get(
    "/admin/messages",
    response_model=list[ContactMessageOut],
    dependencies=[Depends(require_admin)],
    summary="[Admin] Lister les messages de contact",
)
async def admin_list_messages(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ContactMessage).order_by(ContactMessage.created_at.desc()))
    msgs = result.scalars().all()
    return [
        ContactMessageOut(
            id=m.id,
            name=m.name,
            email=m.email,
            phone=m.phone,
            need_type=m.need_type,
            site_url=m.site_url,
            message=m.message,
            status=m.status,
            created_at=m.created_at.isoformat(),
        )
        for m in msgs
    ]


@router.patch(
    "/admin/messages/{msg_id}/status",
    dependencies=[Depends(require_admin)],
    summary="[Admin] Changer le statut d'un message",
    responses={404: {"description": "Message introuvable"}},
)
async def admin_update_status(
    msg_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
):
    allowed = {"new", "handled", "archived"}
    new_status = body.get("status", "")
    if new_status not in allowed:
        raise HTTPException(status_code=422, detail=f"Statut invalide. Valeurs : {allowed}")
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == msg_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message introuvable")
    msg.status = new_status
    await db.commit()
    return {"message": "Statut mis à jour."}
