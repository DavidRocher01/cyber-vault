"""Affordances de test reservees au DEV_MODE (dev local + CI E2E).

Ces endpoints n'existent PAS en production : chaque route verifie
`settings.is_dev_mode` et renvoie 404 sinon. Ils permettent aux tests E2E
Playwright de se placer dans un etat donne sans clef admin ni acces DB
(ex: devenir consultant RSSI), a l'image du checkout DEV_MODE sans Stripe.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User


def _require_dev() -> None:
    if not settings.is_dev_mode:
        # En prod : tout le routeur se comporte comme s'il n'existait pas (404),
        # AVANT meme la verification d'auth (pas de fuite d'existence de route).
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")


# Garde au niveau du routeur : _require_dev s'execute avant les dependances de route
# (dont get_current_user), donc 404 pour tous en prod.
router = APIRouter(prefix="/dev", tags=["dev"], dependencies=[Depends(_require_dev)])


@router.post("/become-consultant")
async def become_consultant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Active le role consultant RSSI sur le compte connecte (DEV_MODE only).

    Remplace, pour l'E2E, le toggle admin `PATCH /admin/users/{id}/rssi` qui
    exige la clef ADMIN_API_KEY (absente de l'environnement E2E)."""
    current_user.is_rssi_consultant = True
    await db.commit()
    return {"id": current_user.id, "is_rssi_consultant": True}
