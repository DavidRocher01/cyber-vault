import asyncio
import csv
import io
import os
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user
from app.core.pagination import paginate
from app.core.ssrf import assert_no_ssrf
from app.core.utils import safe_json_load
from app.models.finding_status import FindingStatus
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User
from app.schemas.cyberscan import PaginatedScans, ScanOut, ScanTriggerOut
from app.services.scan_service import run_scan
from app.services.subscription_service import get_active_plan

router = APIRouter(prefix="/scans", tags=["scans"])


async def _run_scan_background(scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_scan(scan_id, db)


@router.post("/trigger/{site_id}", response_model=ScanTriggerOut, status_code=202)
async def trigger_scan(
    site_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Site).where(
            Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True
        )
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    assert_no_ssrf(site.url)

    # Sérialise les triggers concurrents du même utilisateur : verrou sur la ligne
    # user tenu jusqu'au commit. Ferme la race check-then-act du quota (deux POST
    # simultanés voyaient le même décompte et créaient chacun un scan).
    await db.execute(select(User.id).where(User.id == current_user.id).with_for_update())

    # Enforce scan frequency based on active subscription plan
    plan = await get_active_plan(db, current_user.id)
    interval_days = plan.scan_interval_days if plan else 30

    # Statuts "en vol" : un scan pending/running compte déjà dans le quota,
    # sinon des triggers concurrents le contourneraient (il n'est pas encore "done").
    in_flight = ("pending", "running")

    # Free plan: 1 scan total ever across all sites (en vol ou terminé)
    if plan and plan.price_eur == 0:
        total_result = await db.execute(
            select(func.count(Scan.id))
            .join(Site, Scan.site_id == Site.id)
            .where(
                Site.user_id == current_user.id,
                Scan.status.in_((*in_flight, "done")),
            )
        )
        if total_result.scalar() >= 1:
            raise HTTPException(
                status_code=403,
                detail="Le plan gratuit inclut 1 scan unique. Passez à un plan payant pour continuer.",
            )

    # Enforce interval globally across all user sites to prevent bypass via delete+recreate
    if interval_days > 0:
        from datetime import timedelta

        since = datetime.now(UTC) - timedelta(days=interval_days)
        max_scans = plan.max_sites if plan else 1
        recent_result = await db.execute(
            select(func.count(Scan.id))
            .join(Site, Scan.site_id == Site.id)
            .where(
                Site.user_id == current_user.id,
                or_(
                    Scan.status.in_(in_flight),
                    and_(Scan.status == "done", Scan.finished_at >= since),
                ),
            )
        )
        if recent_result.scalar() >= max_scans:
            raise HTTPException(
                status_code=429,
                detail=f"Limite de scans atteinte. Prochain scan disponible dans {interval_days} jour(s) selon votre plan.",
            )

    scan = Scan(site_id=site_id, status="pending")
    db.add(scan)
    await db.flush()
    await db.refresh(scan)
    background_tasks.add_task(_run_scan_background, scan.id)
    await db.commit()
    return {"scan_id": scan.id, "message": "Scan lancé en arrière-plan"}


@router.get("/site/{site_id}", response_model=PaginatedScans)
async def list_scans(
    site_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Site non trouvé")

    return await paginate(
        db,
        base_query=select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc()),
        count_query=select(func.count()).where(Scan.site_id == site_id),
        page=page,
        per_page=per_page,
    )


@router.get("/site/{site_id}/export")
async def export_scans_csv(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export scan history as CSV."""
    result = await db.execute(
        select(Site).where(Site.id == site_id, Site.user_id == current_user.id)
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scans_result = await db.execute(
        select(Scan).where(Scan.site_id == site_id).order_by(Scan.created_at.desc())
    )
    scans = scans_result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Site", "Statut", "Résultat", "Créé le", "Terminé le", "Durée (s)"])
    for s in scans:
        duration = ""
        if s.started_at and s.finished_at:
            duration = str(int((s.finished_at - s.started_at).total_seconds()))
        writer.writerow(
            [
                s.id,
                site.url,
                s.status,
                s.overall_status or "",
                s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "",
                s.finished_at.strftime("%Y-%m-%d %H:%M") if s.finished_at else "",
                duration,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=rochercybersecurite_site_{site_id}.csv"
        },
    )


@router.get("/{scan_id}", response_model=ScanOut)
async def get_scan(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    return scan


@router.get("/{scan_id}/pdf")
async def download_pdf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    if scan.status != "done" or not scan.pdf_path:
        raise HTTPException(status_code=404, detail="Rapport PDF non disponible")

    return FileResponse(
        path=scan.pdf_path,
        media_type="application/pdf",
        filename=f"rochercybersecurite_rapport_{scan_id}.pdf",
    )


@router.get("/{scan_id}/pdf/branded")
async def download_branded_pdf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a white-label management summary PDF using the user's brand profile."""
    from app.models.brand_profile import BrandProfile
    from app.services.branded_scan_pdf import (
        _compute_score,
        _extract_findings,
        generate_branded_pdf,
    )

    scan_result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == current_user.id)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    if scan.status != "done":
        raise HTTPException(status_code=404, detail="Scan non terminé")

    site_result = await db.execute(select(Site).where(Site.id == scan.site_id))
    site = site_result.scalar_one_or_none()
    domain = site.url if site else "inconnu"

    brand_result = await db.execute(
        select(BrandProfile).where(BrandProfile.user_id == current_user.id)
    )
    brand = brand_result.scalar_one_or_none()

    company_name = brand.company_name if brand else "Rocher Cybersécurité"
    accent_color = brand.accent_color if brand else "#06b6d4"
    logo_b64 = brand.logo_b64 if brand else None

    findings = _extract_findings(scan.results_json)
    score = _compute_score(findings, scan.overall_status)
    scan_date = (
        (scan.finished_at or scan.created_at).strftime("%d/%m/%Y")
        if (scan.finished_at or scan.created_at)
        else ""
    )

    pdf_bytes = await asyncio.to_thread(
        generate_branded_pdf,
        company_name=company_name,
        accent_color=accent_color,
        logo_b64=logo_b64,
        domain=domain,
        overall_status=scan.overall_status or "OK",
        score_pct=score,
        scan_date=scan_date,
        findings=findings,
    )

    safe_company = "".join(c if c.isalnum() else "_" for c in company_name)[:30]
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="rochercybersecurite_{safe_company}_{scan_id}.pdf"'
        },
    )


_REMEDIATION_META: dict[str, tuple[str, str]] = {
    "ufw": ("ufw_setup.sh", "text/x-sh"),
    "ssh": ("ssh_hardening.sh", "text/x-sh"),
    "robots": ("robots.txt", "text/plain"),
    "nginx_waf": ("nginx_waf_ratelimit.conf", "text/plain"),
    "fastapi": ("fastapi_security_middleware.py", "text/x-python"),
    "upgrade": ("upgrade_deps.sh", "text/x-sh"),
    "nginx_ssl": ("nginx_ssl_hardening.conf", "text/plain"),
    "fastapi_cors": ("fastapi_cors_fix.py", "text/x-python"),
    "nginx_cors": ("nginx_cors_fix.conf", "text/plain"),
    "fastapi_cookie": ("fastapi_cookie_security.py", "text/x-python"),
    "nginx_methods": ("nginx_http_methods.conf", "text/plain"),
    "nginx_clickjacking": ("nginx_clickjacking.conf", "text/plain"),
    "fastapi_clickjacking": ("fastapi_clickjacking.py", "text/x-python"),
    "nginx_dirlist": ("nginx_directory_listing.conf", "text/plain"),
    "fastapi_open_redirect": ("fastapi_open_redirect.py", "text/x-python"),
    "dns_email": ("dns_email_security.txt", "text/plain"),
}


@router.get("/{scan_id}/remediation/{script_key}")
async def download_remediation_script(
    scan_id: int,
    script_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a generated remediation script for a completed scan."""
    if script_key not in _REMEDIATION_META:
        raise HTTPException(status_code=404, detail="Script inconnu")

    result = await db.execute(
        select(Scan)
        .join(Site, Site.id == Scan.site_id)
        .where(Scan.id == scan_id, Site.user_id == current_user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    if scan.status != "done" or not scan.results_json:
        raise HTTPException(status_code=404, detail="Scripts non disponibles")

    results = safe_json_load(scan.results_json, {})
    script_path = results.get("_meta", {}).get("remediation_scripts", {}).get(script_key)

    # If file exists on disk, serve it directly
    if script_path and os.path.isfile(script_path):
        filename, media_type = _REMEDIATION_META[script_key]
        return FileResponse(path=script_path, media_type=media_type, filename=filename)

    # File missing on disk — regenerate on-the-fly from scan data stored in DB
    try:
        import sys
        import tempfile

        if "/cyber-scanner" not in sys.path:
            sys.path.insert(0, "/cyber-scanner")
        from scanner.remediation import generate_remediation

        target_url = results.get("_meta", {}).get("url", "unknown")

        with tempfile.TemporaryDirectory() as tmpdir:
            paths = generate_remediation(
                target_url=target_url,
                port_result=results.get("ports") or None,
                headers_result=results.get("headers") or None,
                sca_result=None,
                ssl_result=results.get("ssl") or None,
                cors_result=results.get("cors") or None,
                cookie_result=results.get("cookies") or None,
                http_methods_result=results.get("http_methods") or None,
                clickjacking_result=results.get("clickjacking") or None,
                directory_listing_result=results.get("directory_listing") or None,
                open_redirect_result=results.get("open_redirect") or None,
                robots_result=results.get("robots") or None,
                email_result=results.get("email") or None,
                waf_result=results.get("waf") or None,
                output_dir=tmpdir,
            )
            if script_key not in paths:
                raise HTTPException(status_code=404, detail="Script non disponible pour ce scan")

            filename, media_type = _REMEDIATION_META[script_key]
            with open(paths[script_key], encoding="utf-8") as f:
                content = f.read()

        return StreamingResponse(
            iter([content.encode("utf-8")]),
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except (OSError, FileNotFoundError, ImportError):
        raise HTTPException(status_code=404, detail="Script non trouvé")


# ── Finding status (suivi de correction) ─────────────────────────────────────

VALID_STATUSES = {"todo", "in_progress", "resolved", "accepted_risk"}


async def _get_owned_site(site_id: int, user: User, db: AsyncSession) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.user_id == user.id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    return site


@router.get("/site/{site_id}/finding-status")
async def list_finding_statuses(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_owned_site(site_id, current_user, db)
    rows = await db.execute(select(FindingStatus).where(FindingStatus.site_id == site_id))
    return [
        {
            "module_key": r.module_key,
            "status": r.status,
            "note": r.note,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows.scalars().all()
    ]


@router.put("/site/{site_id}/finding-status/{module_key}")
async def upsert_finding_status(
    site_id: int,
    module_key: str,
    status: str = Body(..., embed=True),
    note: str | None = Body(None, embed=True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Statut invalide. Valeurs acceptées : {VALID_STATUSES}",
        )

    await _get_owned_site(site_id, current_user, db)

    result = await db.execute(
        select(FindingStatus).where(
            FindingStatus.site_id == site_id,
            FindingStatus.module_key == module_key,
        )
    )
    row = result.scalar_one_or_none()

    if row:
        row.status = status
        row.note = note
        row.updated_at = datetime.now(UTC)
    else:
        row = FindingStatus(
            site_id=site_id,
            module_key=module_key,
            status=status,
            note=note,
            updated_at=datetime.now(UTC),
        )
        db.add(row)

    await db.commit()
    return {
        "module_key": row.module_key,
        "status": row.status,
        "note": row.note,
        "updated_at": row.updated_at.isoformat(),
    }
