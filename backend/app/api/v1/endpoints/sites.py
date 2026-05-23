import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.site import Site
from app.models.scan import Scan
from app.schemas.cyberscan import SiteCreate, SiteOut
from app.services.subscription_service import get_active_plan

router = APIRouter(prefix="/sites", tags=["sites"])


@router.get("", response_model=list[SiteOut])
async def list_sites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Site).where(Site.user_id == current_user.id, Site.is_active == True)
    )
    return result.scalars().all()


@router.post("", response_model=SiteOut, status_code=201)
async def add_site(
    payload: SiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = await get_active_plan(db, current_user.id)
    max_sites = plan.max_sites if plan else 0
    if max_sites == 0:
        raise HTTPException(status_code=403, detail="Abonnement requis pour ajouter un site")

    count_result = await db.execute(
        select(func.count(Site.id)).where(Site.user_id == current_user.id, Site.is_active == True)
    )
    current_count = count_result.scalar()
    if current_count >= max_sites:
        raise HTTPException(status_code=403, detail=f"Limite de {max_sites} site(s) atteinte pour votre formule")

    url = payload.url
    # Reject non-web protocols explicitly before auto-correction
    if url.startswith(("ftp://", "ftps://", "javascript:", "data:", "file://")):
        raise HTTPException(status_code=422, detail="Protocole non supporté. Utilisez http:// ou https://")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    site = Site(user_id=current_user.id, url=url, name=payload.name)
    db.add(site)
    await db.commit()
    await db.refresh(site)
    return site


@router.delete("/{site_id}", status_code=204)
async def delete_site(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    site.is_active = False
    await db.commit()


@router.get("/{site_id}/subdomains")
async def get_site_subdomains(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return DNS/subdomain results from the latest completed scan for the site."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scan_result = await db.execute(
        select(Scan)
        .where(Scan.site_id == site_id, Scan.status == "done", Scan.results_json.isnot(None))
        .order_by(Scan.finished_at.desc())
        .limit(1)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan or not scan.results_json:
        return {"site_url": site.url, "subdomains": [], "zone_transfer": None, "scan_date": None}

    try:
        results = json.loads(scan.results_json)
        dns = results.get("dns") or {}
    except Exception:
        dns = {}

    return {
        "site_url": site.url,
        "subdomains": dns.get("found", []),
        "zone_transfer": dns.get("zone_transfer"),
        "total_found": dns.get("total_found", 0),
        "scan_date": scan.finished_at,
    }
