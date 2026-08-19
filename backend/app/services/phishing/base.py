"""Frontiere de transaction — voir la docstring de `commit`."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.phishing_templates import (
    get_awareness_html as get_awareness_html,  # re-export (facade service)
)
from app.services.phishing_templates import (
    get_expired_html as get_expired_html,
)
from app.services.phishing_templates import (
    get_landing_html as get_landing_html,
)
from app.services.phishing_templates import (
    get_pixel_gif as get_pixel_gif,
)


async def commit(db: AsyncSession) -> None:
    """Valide la transaction courante (mutations staged par les fonctions ci-dessous).

    Les fonctions de mutation (create/update/upload/launch...) se contentent de
    `flush()` — elles NE committent PAS — afin de laisser l'endpoint décider de la
    frontière de transaction. C'est volontaire : certaines validations métier ne
    peuvent avoir lieu qu'APRÈS le flush (ex. plafond de cibles d'un plan calculé
    sur le total réel dans `upload_targets`). En cas d'échec, l'endpoint lève une
    HTTPException SANS appeler `commit`, et `get_db` annule le flush.

    La décision commit-vs-rollback dépend donc de la validation HTTP, que la couche
    service ne doit pas connaître (règle CLAUDE.md) : l'endpoint garde l'arbitrage
    et délègue ici la seule opération DB.
    """
    await db.commit()
