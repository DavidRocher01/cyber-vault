from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.utils import safe_json_load
from app.models.rssi_client import RssiClient
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User
from app.schemas.cyberscan import SiteCreate, SiteOut
from app.services import phishing_service
from app.services.subscription_service import get_effective_max_sites

router = APIRouter(prefix="/sites", tags=["sites"])


async def _get_owned_site(site_id: int, user_id: int, db: AsyncSession) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.user_id == user_id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    return site


def _site_domain(site: Site) -> str:
    url = site.url if "://" in site.url else f"https://{site.url}"
    return (urlparse(url).hostname or "").lower()


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
    max_sites = await get_effective_max_sites(db, current_user.id)
    if max_sites == 0:
        raise HTTPException(status_code=403, detail="Abonnement requis pour ajouter un site")

    # max_sites < 0 => plan a un nombre de sites illimité (ex. Gratuit) : pas de limite.
    if max_sites > 0:
        count_result = await db.execute(
            select(func.count(Site.id)).where(
                Site.user_id == current_user.id, Site.is_active == True
            )
        )
        current_count = count_result.scalar()
        if current_count >= max_sites:
            raise HTTPException(
                status_code=403,
                detail=f"Limite de {max_sites} site(s) atteinte pour votre formule",
            )

    url = payload.url
    # Reject non-web protocols explicitly before auto-correction
    if url.startswith(("ftp://", "ftps://", "javascript:", "data:", "file://")):
        raise HTTPException(
            status_code=422,
            detail="Protocole non supporté. Utilisez http:// ou https://",
        )
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    rssi_client_id = payload.rssi_client_id
    if rssi_client_id is not None:
        client_result = await db.execute(
            select(RssiClient).where(
                RssiClient.id == rssi_client_id,
                RssiClient.consultant_user_id == current_user.id,
            )
        )
        if not client_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Client RSSI non trouvé")

    site = Site(
        user_id=current_user.id,
        url=url,
        name=payload.name,
        rssi_client_id=rssi_client_id,
    )
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


# ── Vérification de propriété du domaine (H2b) ─────────────────────────────────
# Débloque l'analyse de ports (nmap, module intrusif) : niveau 2 = passif libre /
# intrusif réservé aux domaines dont l'utilisateur a prouvé la propriété.


@router.get("/{site_id}/domain")
async def get_site_domain_status(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _get_owned_site(site_id, current_user.id, db)
    domain = _site_domain(site)
    verified = (
        await phishing_service.is_domain_verified(current_user.id, domain, db) if domain else False
    )
    return {"domain": domain, "verified": verified}


@router.post("/{site_id}/domain/verify", status_code=201)
async def request_site_domain_verify(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Émet (ou renouvelle) le token de vérification DNS TXT pour le domaine du site."""
    site = await _get_owned_site(site_id, current_user.id, db)
    domain = _site_domain(site)
    if not domain:
        raise HTTPException(status_code=422, detail="Domaine du site invalide")
    record = await phishing_service.request_domain_verification(current_user.id, domain, db)
    await db.commit()
    return {
        "domain": record.domain,
        "verified": record.verified,
        "verification_token": record.verification_token,
        "dns_record_name": f"_rocher-verify.{record.domain}",
        "dns_record_type": "TXT",
        "dns_record_value": record.verification_token,
        "instructions": (
            f"Ajoutez cet enregistrement DNS TXT sur votre domaine :\n"
            f"  Nom : _rocher-verify.{record.domain}\n"
            f"  Type : TXT\n"
            f"  Valeur : {record.verification_token}\n"
            "Puis cliquez sur « Vérifier » (propagation : jusqu'à ~10 min)."
        ),
    }


@router.post("/{site_id}/domain/verify/check")
async def check_site_domain_verify(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Vérifie le TXT DNS ; si présent, le domaine est marqué vérifié (débloque l'intrusif)."""
    site = await _get_owned_site(site_id, current_user.id, db)
    domain = _site_domain(site)
    record = await phishing_service.get_domain_verification(current_user.id, domain, db)
    if not record:
        raise HTTPException(
            status_code=404,
            detail="Aucune demande de vérification pour ce domaine. Lancez-la d'abord.",
        )
    verified = await phishing_service.check_domain_verification(record, db)
    if verified:
        await db.commit()
    return {
        "domain": domain,
        "verified": verified,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
    }


@router.get("/{site_id}/subdomains")
async def get_site_subdomains(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return DNS/subdomain results from the latest completed scan for the site."""
    result = await db.execute(
        select(Site).where(
            Site.id == site_id, Site.user_id == current_user.id, Site.is_active == True
        )
    )
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")

    scan_result = await db.execute(
        select(Scan)
        .where(
            Scan.site_id == site_id,
            Scan.status == "done",
            Scan.results_json.isnot(None),
        )
        .order_by(Scan.finished_at.desc())
        .limit(1)
    )
    scan = scan_result.scalar_one_or_none()
    if not scan or not scan.results_json:
        return {
            "site_url": site.url,
            "subdomains": [],
            "zone_transfer": None,
            "scan_date": None,
        }

    results = safe_json_load(scan.results_json, {})
    dns = results.get("dns") or {}

    return {
        "site_url": site.url,
        "subdomains": dns.get("found", []),
        "zone_transfer": dns.get("zone_transfer"),
        "total_found": dns.get("total_found", 0),
        "scan_date": scan.finished_at,
    }
