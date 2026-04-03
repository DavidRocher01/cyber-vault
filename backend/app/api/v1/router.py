from fastapi import APIRouter

from app.api.v1.endpoints import auth, vault, plans, subscriptions, sites, scans, webhooks, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(vault.router)
api_router.include_router(plans.router)
api_router.include_router(subscriptions.router)
api_router.include_router(sites.router)
api_router.include_router(scans.router)
api_router.include_router(webhooks.router)
api_router.include_router(users.router)
