import asyncio
import csv
import io
import os
from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, get_db
from app.core.deps import get_current_user, require_min_tier
from app.core.limiter import limiter
from app.core.ssrf import assert_no_ssrf
from app.core.utils import safe_json_load
from app.models.site import Site
from app.models.user import User
from app.schemas.cyberscan import PaginatedScans, ScanOut, ScanTriggerOut
from app.services import scan_query_service
from app.services.scan_service import run_scan
from app.services.storage import lire_rapport
from app.services.subscription_service import get_active_plan

router = APIRouter(prefix="/scans", tags=["scans"])


async def _run_scan_background(scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_scan(scan_id, db)


@router.post("/trigger/{site_id}", response_model=ScanTriggerOut, status_code=202)
@limiter.limit("10/minute")
async def trigger_scan(
    request: Request,
    site_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await scan_query_service.get_owned_active_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    assert_no_ssrf(site.url)

    # Sérialise les triggers concurrents du même utilisateur : verrou sur la ligne
    # user tenu jusqu'au commit. Ferme la race check-then-act du quota (deux POST
    # simultanés voyaient le même décompte et créaient chacun un scan).
    await scan_query_service.lock_user_row(db, current_user.id)

    # Enforce scan frequency based on active subscription plan
    plan = await get_active_plan(db, current_user.id)
    interval_days = plan.scan_interval_days if plan else 30

    # Statuts "en vol" : un scan pending/running compte déjà dans le quota,
    # sinon des triggers concurrents le contourneraient (il n'est pas encore "done").
    in_flight = ("pending", "running")

    # Enforce interval globally across all user sites to prevent bypass via delete+recreate.
    # Le décompte "scans dans la fenêtre" est plafonné par max_sites du plan.
    # - interval_days <= 1 (plans payants Starter/Pro/Business, scan quotidien) => scans
    #   manuels illimités : seul le garde @limiter.limit("10/minute") subsiste.
    # - max_sites < 0 (Business, sites illimités) => aucun plafond de fréquence.
    # Seul le Gratuit (interval=30, max_sites=1) reste plafonné à 1 scan / 30 jours.
    max_scans = plan.max_sites if plan else 1
    if interval_days > 1 and max_scans >= 0:
        since = datetime.now(UTC) - timedelta(days=interval_days)
        recent = await scan_query_service.count_scans_in_window(
            db, current_user.id, in_flight, since
        )
        if recent >= max_scans:
            raise HTTPException(
                status_code=429,
                detail=f"Limite de scans atteinte. Prochain scan disponible dans {interval_days} jour(s) selon votre plan.",
            )

    scan = await scan_query_service.create_pending_scan(db, site_id)
    background_tasks.add_task(_run_scan_background, scan.id)
    return {"scan_id": scan.id, "message": "Scan lancé en arrière-plan"}


@router.get("/site/{site_id}", response_model=PaginatedScans)
async def list_scans(
    site_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await scan_query_service.get_owned_site(db, site_id, current_user.id):
        raise HTTPException(status_code=404, detail="Site non trouvé")

    return await scan_query_service.paginate_site_scans(db, site_id, page, per_page)


@router.get("/site/{site_id}/export")
async def export_scans_csv(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export scan history as CSV."""
    site = await scan_query_service.get_owned_site(db, site_id, current_user.id)
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scans = await scan_query_service.list_site_scans(db, site_id)

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
    scan = await scan_query_service.get_owned_scan(db, scan_id, current_user.id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    return scan


@router.get("/{scan_id}/pdf")
async def download_pdf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    scan = await scan_query_service.get_owned_scan(db, scan_id, current_user.id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    if scan.status != "done" or not scan.pdf_path:
        raise HTTPException(status_code=404, detail="Rapport PDF non disponible")

    # ON VERIFIE QUE LE RAPPORT EST LA, pas seulement que la base l'affirme.
    #
    # Le 2026-08-09, sept minutes apres un deploiement, cet endpoint a repondu
    # 500 : `FileResponse` recevait un chemin dont le fichier avait disparu avec
    # la tache Fargate remplacee. Une exception non rattrapee, une alarme
    # CloudWatch reveillee, et un utilisateur qui n'apprend rien.
    #
    # Les rapports sont desormais ranges hors du conteneur. Restent les lignes
    # d'avant, dont le chemin ne pointe plus nulle part : elles meritent une
    # phrase utile, pas une erreur serveur.
    contenu = lire_rapport(scan.pdf_path)
    if contenu is None:
        raise HTTPException(
            status_code=404,
            detail="Ce rapport n'est plus disponible. Relancez un scan pour en obtenir un à jour.",
        )

    return Response(
        content=contenu,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="rochercybersecurite_rapport_{scan_id}.pdf"'
            )
        },
    )


@router.get("/{scan_id}/pdf/branded")
async def download_branded_pdf(
    scan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a white-label management summary PDF using the user's brand profile."""
    from app.services.branded_scan_pdf import (
        _compute_score,
        _extract_findings,
        generate_branded_pdf,
    )

    scan = await scan_query_service.get_owned_scan(db, scan_id, current_user.id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan non trouvé")
    if scan.status != "done":
        raise HTTPException(status_code=404, detail="Scan non terminé")

    site = await scan_query_service.get_site(db, scan.site_id)
    domain = site.url if site else "inconnu"

    brand = await scan_query_service.get_brand_profile(db, current_user.id)

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


@router.get(
    "/{scan_id}/remediation/{script_key}",
    dependencies=[Depends(require_min_tier(2))],  # Scripts de remédiation : Starter+
)
async def download_remediation_script(
    scan_id: int,
    script_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a generated remediation script for a completed scan."""
    if script_key not in _REMEDIATION_META:
        raise HTTPException(status_code=404, detail="Script inconnu")

    scan = await scan_query_service.get_owned_scan(db, scan_id, current_user.id)
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
    site = await scan_query_service.get_owned_site(db, site_id, user.id)
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
    rows = await scan_query_service.list_finding_statuses(db, site_id)
    return [
        {
            "module_key": r.module_key,
            "status": r.status,
            "note": r.note,
            "updated_at": r.updated_at.isoformat(),
        }
        for r in rows
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

    row = await scan_query_service.upsert_finding_status(
        db,
        site_id=site_id,
        module_key=module_key,
        status=status,
        note=note,
        now=datetime.now(UTC),
    )
    return {
        "module_key": row.module_key,
        "status": row.status,
        "note": row.note,
        "updated_at": row.updated_at.isoformat(),
    }
