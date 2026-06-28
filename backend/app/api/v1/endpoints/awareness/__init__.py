"""
Awareness sub-package.

Le router principal re-exporte tous les sous-routers avec le prefix /awareness
afin que l'import existant dans router.py reste inchangé :

    from app.api.v1.endpoints import awareness
    api_router.include_router(awareness.router)
"""

from fastapi import APIRouter

from .badges import router as badges_router
from .certificates import router as certificates_router
from .enrollments import router as enrollments_router
from .learners import router as learners_router
from .organizations import router as organizations_router
from .programs import router as programs_router
from .progress import router as progress_router
from .quizzes import router as quizzes_router

router = APIRouter(prefix="/awareness", tags=["awareness"])

router.include_router(organizations_router)
router.include_router(learners_router)
router.include_router(programs_router)
router.include_router(enrollments_router)
router.include_router(progress_router)
router.include_router(quizzes_router)
router.include_router(badges_router)
router.include_router(certificates_router)
