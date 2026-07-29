"""
Public scan endpoints — no authentication required.
Rate limited to 3 scans/hour per IP to prevent abuse.

Gate lead : POST/GET ne renvoient qu'un teaser (sévérités agrégées) ; le rapport
complet n'est révélé qu'après déblocage par email (POST /{token}/unlock).
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, get_db
from app.core.limiter import _get_real_ip, limiter
from app.core.ssrf import assert_no_ssrf
from app.models.public_scan import PublicScan
from app.schemas.public_scan import PublicScanCreate, PublicScanOut, PublicScanUnlockIn
from app.services import email_service, public_scan_service
from app.services.public_scan_service import (
    AlreadyUnlockedError,
    QuotaExceededError,
    ScanNotReadyError,
    run_public_scan,
)

router = APIRouter(prefix="/public-scans", tags=["public-scans"])


async def _run_background(public_scan_id: int) -> None:
    async with AsyncSessionLocal() as db:
        await run_public_scan(public_scan_id, db)


def _teaser(scan: PublicScan) -> PublicScanOut:
    return PublicScanOut.from_orm_obj(
        scan, severity_counts=public_scan_service.compute_severity_counts(scan)
    )


@router.post("", response_model=PublicScanOut, status_code=202)
@limiter.limit("3/hour")
async def create_public_scan(
    payload: PublicScanCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> PublicScanOut:
    url = payload.url.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    try:
        assert_no_ssrf(url)
    except ValueError:
        raise HTTPException(status_code=422, detail="URL non autorisée")

    scan = await public_scan_service.create_public_scan(db, url)
    background_tasks.add_task(_run_background, scan.id)
    return _teaser(scan)


@router.get("/{token}", response_model=PublicScanOut)
async def get_public_scan(
    token: str,
    db: AsyncSession = Depends(get_db),
) -> PublicScanOut:
    scan = await public_scan_service.get_public_scan_by_token(db, token)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan introuvable")
    return _teaser(scan)


@router.post("/{token}/unlock", response_model=PublicScanOut)
@limiter.limit("5/hour")
async def unlock_public_scan(
    token: str,
    payload: PublicScanUnlockIn,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> PublicScanOut:
    """Débloque le rapport complet contre un email + consentement RGPD (single opt-in).

    Durci contre le mailbombing : rate-limit 5/h/IP, email figé au premier déblocage
    (un token = une adresse), et l'email de rapport n'est envoyé QUE lors de la
    transition (jamais sur une ré-consultation idempotente).
    """
    if not payload.consent:
        raise HTTPException(status_code=422, detail="Le consentement est obligatoire")

    ip_hash = public_scan_service.hash_ip(_get_real_ip(request))
    try:
        scan, newly_unlocked = await public_scan_service.unlock_public_scan(
            db, token=token, email=payload.email, ip_hash=ip_hash
        )
    except ScanNotReadyError:
        raise HTTPException(status_code=409, detail="Le scan n'est pas encore terminé")
    except AlreadyUnlockedError:
        raise HTTPException(
            status_code=409,
            detail="Ce rapport a déjà été débloqué avec une autre adresse email.",
        )
    except QuotaExceededError:
        raise HTTPException(
            status_code=429,
            detail=(
                "Quota de rapports gratuits atteint pour cet email. Créez un compte pour continuer."
            ),
        )
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan introuvable")

    # Envoi d'une copie du rapport par email (lead nurturing) — non bloquant, et
    # UNIQUEMENT au déblocage effectif (newly_unlocked) : une ré-consultation avec
    # la même adresse ne redéclenche jamais d'envoi (anti-spam du destinataire).
    if newly_unlocked:
        # Le rapport se consulte sur /demo-result/{token} (le token porte l'état débloqué).
        report_url = f"{settings.FRONTEND_URL}/demo-result/{scan.session_token}"
        background_tasks.add_task(
            email_service.send_public_scan_report,
            scan.email,
            scan.domain or scan.target_url,
            scan.overall_status or "OK",
            report_url,
        )
    return _teaser(scan)
