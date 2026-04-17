from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def get_user_resource(
    db: AsyncSession,
    model_class,
    resource_id: int,
    user_id: int,
    error_msg: str = "Ressource non trouvée",
):
    """SELECT model WHERE id=resource_id AND user_id=user_id, raise 404 if missing."""
    result = await db.execute(
        select(model_class).where(
            model_class.id == resource_id,
            model_class.user_id == user_id,
        )
    )
    resource = result.scalar_one_or_none()
    if not resource:
        raise HTTPException(status_code=404, detail=error_msg)
    return resource
