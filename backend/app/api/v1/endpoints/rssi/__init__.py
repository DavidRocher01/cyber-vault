from fastapi import APIRouter

from .actions import router as actions_router
from .activity import router as activity_router
from .clients import (
    RssiClientCreate,
    RssiClientOut,
    RssiClientUpdate,
    create_client,
    delete_client,
    list_clients,
    update_client,
)
from .clients import (
    router as clients_router,
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
