"""Routes phishing — tracking."""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.core.limiter import limiter
from app.services.phishing import base, tracking

router = APIRouter()

# ---------------------------------------------------------------------------
# Public tracking routes — no authentication (called by email clients / browsers)
# ---------------------------------------------------------------------------


@router.get("/t/{tracking_id}/px", include_in_schema=False)
@limiter.limit("30/minute")
async def tracking_pixel(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Serve 1×1 transparent GIF and record email open."""
    await tracking.record_open(tracking_id, db)
    return Response(
        content=base.get_pixel_gif(),
        media_type="image/gif",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )


@router.get("/t/{tracking_id}/c", include_in_schema=False)
@limiter.limit("10/minute")
async def tracking_click(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Record link click and redirect to the landing page (or expiry page if campaign has ended)."""
    active = await tracking.record_click(tracking_id, db)
    if not active:
        return HTMLResponse(content=tracking.get_expired_html())
    return RedirectResponse(url=f"/phishing/t/{tracking_id}/l", status_code=302)


@router.get("/t/{tracking_id}/l", response_class=HTMLResponse, include_in_schema=False)
@limiter.limit("15/minute")
async def tracking_landing(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Serve the scenario-specific credential-harvesting landing page, or expiry page."""
    scenario_key, landing_base, expired = await tracking.get_landing_context(tracking_id, db)
    if expired:
        return HTMLResponse(content=tracking.get_expired_html())
    return HTMLResponse(content=tracking.get_landing_html(tracking_id, scenario_key, landing_base))


@router.post("/t/{tracking_id}/s", response_class=HTMLResponse, include_in_schema=False)
@limiter.limit("5/minute")
async def tracking_submit(request: Request, tracking_id: str, db: AsyncSession = Depends(get_db)):
    """Record credential submission and return the awareness / education page."""
    scenario_key = await tracking.record_submit(tracking_id, db)
    return HTMLResponse(content=tracking.get_awareness_html(scenario_key))
