from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_client import RssiClient


async def _get_client_or_404(client_id: int, user_id: int, db: AsyncSession) -> RssiClient:
    result = await db.execute(
        select(RssiClient).where(
            RssiClient.id == client_id,
            RssiClient.consultant_user_id == user_id,
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client non trouvé")
    return client
