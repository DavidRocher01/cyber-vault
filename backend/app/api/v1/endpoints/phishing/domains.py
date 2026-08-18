"""Routes phishing — domains."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.cyberscan import DomainStatusOut, DomainVerifyOut
from app.schemas.phishing import (
    LookalikeDomainsOut,
)
from app.services import phishing_service
from app.services.domain_lookalike import generate_lookalikes

from ._shared import (
    DomainCheckRequest,
    DomainVerifyRequest,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Domain verification endpoints
# ---------------------------------------------------------------------------


@router.post("/domain-verify", status_code=status.HTTP_201_CREATED, response_model=DomainVerifyOut)
async def request_domain_verification(
    payload: DomainVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    record = await phishing_service.request_domain_verification(
        current_user.id, payload.domain.lower().strip(), db
    )
    await phishing_service.commit(db)
    return {
        "domain": record.domain,
        "verified": record.verified,
        "verification_token": record.verification_token,
        "dns_record_name": f"_rocher-verify.{record.domain}",
        "dns_record_type": "TXT",
        "dns_record_value": record.verification_token,
        "instructions": (
            f"Ajoutez un enregistrement DNS TXT sur votre domaine :\n"
            f"  Nom : _rocher-verify.{record.domain}\n"
            f"  Type : TXT\n"
            f"  Valeur : {record.verification_token}\n"
            "Puis cliquez sur 'Vérifier' une fois propagé (peut prendre jusqu'à 10 min)."
        ),
    }


@router.post("/domain-verify/check", response_model=DomainStatusOut)
async def check_domain_verification(
    payload: DomainCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    domain = payload.domain.lower().strip()
    record = await phishing_service.get_domain_verification(current_user.id, domain, db)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucune demande de vérification trouvée pour ce domaine. "
            "Lancez d'abord une demande via POST /phishing/domain-verify.",
        )

    verified = await phishing_service.check_domain_verification(record, db)
    if verified:
        await phishing_service.commit(db)
    return {
        "domain": domain,
        "verified": verified,
        "verified_at": record.verified_at.isoformat() if record.verified_at else None,
    }


# ---------------------------------------------------------------------------
# Look-alike domain suggestions (authenticated)
# ---------------------------------------------------------------------------


@router.get("/lookalike-domains", response_model=LookalikeDomainsOut)
async def get_lookalike_domains(
    domain: str = Query(
        ...,
        min_length=3,
        max_length=255,
        description="Target domain, e.g. monentreprise.com",
    ),
    _current_user: User = Depends(get_current_user),
):
    """Return a list of look-alike domain suggestions for the given target domain."""
    suggestions = generate_lookalikes(domain.lower().strip(), max_results=30)
    return {"domain": domain, "suggestions": suggestions}
