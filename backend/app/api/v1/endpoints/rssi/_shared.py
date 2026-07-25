from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rssi_client import RssiClient
from app.services import rssi_client_service


async def _get_client_or_404(client_id: int, user_id: int, db: AsyncSession) -> RssiClient:
    client = await rssi_client_service.get_client_for_consultant(db, client_id, user_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client non trouvé")
    return client
