"""Service des messages de contact / demandes de devis."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact_message import ContactMessage


async def create_contact_message(
    db: AsyncSession,
    *,
    name: str,
    email: str,
    phone: str | None,
    need_type: str,
    site_url: str | None,
    message: str,
) -> ContactMessage:
    msg = ContactMessage(
        name=name,
        email=email,
        phone=phone,
        need_type=need_type,
        site_url=site_url,
        message=message,
        status="new",
        created_at=datetime.now(UTC),
    )
    db.add(msg)
    await db.commit()
    return msg


async def list_contact_messages(db: AsyncSession) -> list[ContactMessage]:
    result = await db.execute(select(ContactMessage).order_by(ContactMessage.created_at.desc()))
    return list(result.scalars().all())


async def get_contact_message(db: AsyncSession, msg_id: int) -> ContactMessage | None:
    result = await db.execute(select(ContactMessage).where(ContactMessage.id == msg_id))
    return result.scalar_one_or_none()


async def set_message_status(
    db: AsyncSession, msg: ContactMessage, new_status: str
) -> ContactMessage:
    msg.status = new_status
    await db.commit()
    return msg
