from fastapi import APIRouter

from .activity import router as activity_router
from .actions import router as actions_router
from .clients import (
    router as clients_router,
    RssiClientCreate,
    RssiClientUpdate,
    RssiClientOut,
    list_clients,
    create_client,
    update_client,
    delete_client,
)
from .dashboard import router as dashboard_router
from .deliverables import router as deliverables_router
from .profile import router as profile_router
from .report import router as report_router
from .visits import router as visits_router

router = APIRouter(prefix="/rssi", tags=["rssi"])

router.include_router(clients_router)
router.include_router(visits_router)
router.include_router(actions_router)
router.include_router(dashboard_router)
router.include_router(activity_router)
router.include_router(report_router)
router.include_router(deliverables_router)
router.include_router(profile_router)
