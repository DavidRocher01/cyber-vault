from fastapi import APIRouter, BackgroundTasks, Request, status
from app.core.limiter import limiter
from app.core.config import settings
from app.schemas.contact import ContactIn
from app.services.email_service import send_contact_email

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("", status_code=status.HTTP_200_OK)
@limiter.limit("3/hour")
async def submit_contact(
    request: Request,
    payload: ContactIn,
    background_tasks: BackgroundTasks,
):
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
