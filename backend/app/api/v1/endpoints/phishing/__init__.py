"""Sous-paquet phishing.

Le routeur principal agrege les sous-routeurs sous le prefixe /phishing, afin
que l'import existant dans `router.py` reste inchange :

    from app.api.v1.endpoints import phishing
    api_router.include_router(phishing.router)

Ce fichier faisait 764 lignes — le plus gros endpoint du depot — alors que les
domaines sensibilisation et RSSI etaient deja decoupes de cette facon.
"""

from fastapi import APIRouter

from .campaigns import router as campaigns_router
from .domains import router as domains_router
from .launch import router as launch_router
from .report import router as report_router
from .targets import router as targets_router
from .tracking import router as tracking_router

router = APIRouter(prefix="/phishing", tags=["phishing"])

# L'ordre reprend celui du fichier d'origine.
router.include_router(campaigns_router)
router.include_router(targets_router)
router.include_router(launch_router)
router.include_router(report_router)
router.include_router(domains_router)
router.include_router(tracking_router)
