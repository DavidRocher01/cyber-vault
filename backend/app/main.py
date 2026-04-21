import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

import app.models  # noqa: F401 — register all models with Base.metadata

from app.__version__ import __version__
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import get_db
from app.core.limiter import limiter
from app.core.logging import setup_logging
from app.services.scheduler import start_scheduler, stop_scheduler

setup_logging(settings.APP_ENV)

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=settings.APP_ENV,
    )
    logger.info("Sentry initialisé")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
        return response


async def _seed_plans() -> None:
    """Insert default plans if they don't exist yet (idempotent).
    stripe_price_id is intentionally excluded — set it via admin or migration
    to avoid overwriting live Stripe IDs on restart.
    """
    from app.core.database import AsyncSessionLocal
    from app.models.plan import Plan
    from sqlalchemy import select

    PLANS = [
        {"name": "free",     "display_name": "Gratuit",  "price_eur": 0,    "max_sites": 1,  "scan_interval_days": 0,  "tier_level": 1},
        {"name": "starter",  "display_name": "Starter",  "price_eur": 990,  "max_sites": 1,  "scan_interval_days": 30, "tier_level": 2},
        {"name": "pro",      "display_name": "Pro",       "price_eur": 3990, "max_sites": 3,  "scan_interval_days": 7,  "tier_level": 3},
        {"name": "business", "display_name": "Business",  "price_eur": 4990, "max_sites": 10, "scan_interval_days": 1,  "tier_level": 4},
    ]
    async with AsyncSessionLocal() as db:
        for plan_data in PLANS:
            result = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
            if not result.scalar_one_or_none():
                db.add(Plan(**plan_data))
        await db.commit()
    logger.info("Plans seeded")


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    on_startup=[_seed_plans, start_scheduler],
    on_shutdown=[stop_scheduler],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

app.include_router(api_router)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception:
        db_status = "error"
    overall = "ok" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "version": __version__,
        "environment": settings.APP_ENV,
        "database": db_status,
    }
