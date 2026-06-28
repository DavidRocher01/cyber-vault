from contextlib import asynccontextmanager

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
from app.core.database import AsyncSessionLocal, get_db
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
            "img-src 'self' data: https://rochercybersecurite.com https://*.rochercybersecurite.com https://www.gravatar.com; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
        if settings.APP_ENV == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response


async def _seed_plans() -> None:
    """Insert default plans if they don't exist yet (idempotent).
    stripe_price_id is intentionally excluded — set it via admin or migration
    to avoid overwriting live Stripe IDs on restart.
    """
    from sqlalchemy import select

    from app.core.database import AsyncSessionLocal
    from app.models.plan import Plan

    PLANS = [
        {
            "name": "free",
            "display_name": "Gratuit",
            "price_eur": 0,
            "max_sites": 1,
            "scan_interval_days": 0,
            "tier_level": 1,
        },
        {
            "name": "starter",
            "display_name": "Surveillance Starter",
            "price_eur": 1490,
            "max_sites": 1,
            "scan_interval_days": 7,
            "tier_level": 2,
        },
        {
            "name": "pro",
            "display_name": "Surveillance Pro",
            "price_eur": 4900,
            "max_sites": 5,
            "scan_interval_days": 7,
            "tier_level": 3,
        },
        {
            "name": "business",
            "display_name": "Surveillance Business",
            "price_eur": 14900,
            "max_sites": 15,
            "scan_interval_days": 1,
            "tier_level": 4,
        },
    ]
    async with AsyncSessionLocal() as db:
        for plan_data in PLANS:
            result = await db.execute(select(Plan).where(Plan.name == plan_data["name"]))
            if not result.scalar_one_or_none():
                db.add(Plan(**plan_data))
        await db.commit()
    logger.info("Plans seeded")


async def _seed_awareness_badges() -> None:
    """Seed / upsert the 20 awareness badge definitions (idempotent)."""
    from app.services.awareness_gamification import seed_badges

    async with AsyncSessionLocal() as db:
        count = await seed_badges(db)
    if count:
        logger.info(f"Awareness badges seeded: {count} created")


async def _import_awareness_content() -> None:
    """Import NIS2 awareness content from content/fr/ if no programs exist yet (idempotent)."""
    from pathlib import Path

    from app.core.database import AsyncSessionLocal
    from app.services.awareness_content_importer import import_from_directory

    content_dir = Path(__file__).parent.parent.parent / "content" / "fr"
    if not content_dir.exists():
        logger.warning(f"Awareness content directory not found: {content_dir}")
        return

    async with AsyncSessionLocal() as db:
        try:
            summary = await import_from_directory(db, content_dir)
            logger.info(
                f"Awareness content synced: {summary['programs']} programmes, "
                f"{summary['modules']} modules"
            )
            if summary.get("errors"):
                for e in summary["errors"]:
                    logger.warning(f"Awareness content import error: {e}")
        except Exception as exc:
            logger.error(f"Awareness content auto-import failed: {exc}")


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI):
    await _seed_plans()
    await _seed_awareness_badges()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

app.include_router(api_router)

# Local file upload serving (dev only — in prod files go to S3)
if not settings.S3_BUCKET_NAME:
    from pathlib import Path

    from fastapi.staticfiles import StaticFiles

    _upload_dir = Path("uploads")
    _upload_dir.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(_upload_dir)), name="uploads")


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select

    from app.models.blog_post import BlogPost  # noqa: F401

    base = "https://rochercybersecurite.com"
    static_urls = [
        ("", "weekly", "1.0"),
        ("/", "weekly", "0.9"),
        ("/scan-gratuit", "weekly", "0.9"),
        ("/contact", "monthly", "0.8"),
        ("/reserver", "monthly", "0.8"),
        ("/ressources", "weekly", "0.7"),
        ("/bonnes-pratiques", "monthly", "0.6"),
        ("/blog", "daily", "0.8"),
        ("/nis2", "monthly", "0.6"),
        ("/iso27001", "monthly", "0.6"),
        ("/cgu", "yearly", "0.3"),
        ("/cgv", "yearly", "0.3"),
        ("/dpa", "yearly", "0.3"),
        ("/politique-confidentialite", "yearly", "0.3"),
        ("/mentions-legales", "yearly", "0.3"),
    ]

    result = await db.execute(
        select(BlogPost.slug, BlogPost.updated_at).where(BlogPost.is_published == True)  # noqa: E712
    )
    blog_slugs = result.all()

    urls = "\n".join(
        f"  <url><loc>{base}{path}</loc><changefreq>{freq}</changefreq><priority>{prio}</priority></url>"
        for path, freq, prio in static_urls
    )
    for slug, updated_at in blog_slugs:
        lastmod = f"<lastmod>{updated_at.date().isoformat()}</lastmod>" if updated_at else ""
        urls += f"\n  <url><loc>{base}/blog/{slug}</loc>{lastmod}<changefreq>monthly</changefreq><priority>0.7</priority></url>"

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>"""

    from fastapi.responses import Response as FastAPIResponse

    return FastAPIResponse(content=xml, media_type="application/xml")


@app.get("/robots.txt", include_in_schema=False)
async def robots():
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        "User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /admin\n"
        "Sitemap: https://rochercybersecurite.com/sitemap.xml\n"
    )


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


@app.get("/health/deep")
async def health_deep(db: AsyncSession = Depends(get_db)):
    """Deep health check — tests DB + external services. Use for monitoring (not ALB)."""
    import asyncio as _asyncio

    checks: dict[str, str] = {}

    # Database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {str(exc)[:100]}"

    # Stripe
    if settings.STRIPE_SECRET_KEY:
        try:
            import stripe as _stripe

            _stripe.api_key = settings.STRIPE_SECRET_KEY
            await _asyncio.to_thread(_stripe.Balance.retrieve)
            checks["stripe"] = "ok"
        except Exception as exc:
            checks["stripe"] = f"error: {str(exc)[:100]}"

    # Resend
    if settings.RESEND_API_KEY:
        try:
            import resend as _resend

            _resend.api_key = settings.RESEND_API_KEY
            await _asyncio.to_thread(_resend.Domains.list)
            checks["resend"] = "ok"
        except Exception as exc:
            checks["resend"] = f"error: {str(exc)[:100]}"

    # S3
    if settings.S3_BUCKET_NAME:
        try:
            import boto3 as _boto3

            client = _boto3.client("s3", region_name=settings.AWS_REGION)
            await _asyncio.to_thread(client.head_bucket, Bucket=settings.S3_BUCKET_NAME)
            checks["s3"] = "ok"
        except Exception as exc:
            checks["s3"] = f"error: {str(exc)[:100]}"

    all_ok = all(v == "ok" for v in checks.values())
    return {
        "status": "healthy" if all_ok else "degraded",
        "version": __version__,
        "environment": settings.APP_ENV,
        "checks": checks,
    }
