"""Onglet Acquisition du back-office — lecture seule.

Conception : `docs/ANALYTICS.md`.

Ces routes utilisent `get_admin_user`, **pas** `require_admin` : elles n'acceptent
qu'un compte administrateur identifié, jamais la clé partagée `X-Admin-Key`. Ce
qu'on construit maintenant ne doit pas hériter du secret qu'on est en train de
retirer (cf. `docs/S6_INFRA_CHECKLIST.md` §0).
"""

from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_admin_user
from app.models.user import User
from app.services import acquisition_service

router = APIRouter(prefix="/admin/acquisition", tags=["admin"])

# Fenêtres proposées par l'interface. Un entier libre laisserait demander
# 100 000 jours et balayer toute la table.
FENETRES: dict[str, int] = {"30j": 30, "90j": 90, "12m": 365}


@router.get("", summary="[Admin] Sources d'acquisition, tunnel et pages d'entrée")
async def vue_acquisition(
    fenetre: Literal["30j", "90j", "12m"] = "90j",
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> dict:
    """Tout ce qu'affiche l'onglet, en un appel.

    Un seul aller-retour plutôt que trois : les trois vues se lisent ensemble,
    sur la même fenêtre, et se contrediraient si elles étaient chargées à des
    instants différents.
    """
    jours = FENETRES[fenetre]

    etapes = await acquisition_service.tunnel(db, jours=jours)
    sources = await acquisition_service.par_source(db, jours=jours)
    pages = await acquisition_service.par_page(db, jours=jours)
    mrr_actif = await acquisition_service.mrr_par_source_confirme(db, jours=jours)

    return {
        "fenetre": fenetre,
        "jours": jours,
        "tunnel": etapes,
        "sources": sources,
        "pages": pages,
        # Signé sur la période VS encore actif aujourd'hui : deux chiffres
        # différents, et les confondre ferait surestimer le revenu récurrent.
        "mrr_signe_cents": sum(s["mrr_cents"] for s in sources),
        "mrr_actif_cents": mrr_actif,
        # L'interface s'appuie dessus pour distinguer « aucune donnée » d'un
        # « zéro » mesuré — le premier appelle une explication, pas un tableau vide.
        "collecte_vide": not any(etapes.values()),
    }
