"""
Audit collaboratif — inviter des collaborateurs sur un site avec rôles granulaires.
Roles: viewer (lecture seule), auditor (lecture + déclencher scan), manager (tout sauf supprimer)
"""

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.collab import SiteCollaborator
from app.models.site import Site
from app.models.user import User

router = APIRouter(prefix="/collab", tags=["collab"])

VALID_ROLES = {"viewer", "auditor", "manager"}

ROLE_LABELS = {
    "viewer": "Lecteur — consulte les résultats des scans",
    "auditor": "Auditeur — peut déclencher des scans",
    "manager": "Manager — peut gérer les paramètres du site",
}


class CollabOut(BaseModel):
    id: int
    site_id: int
    email: str
    role: str
    status: str
    invited_at: datetime
    accepted_at: datetime | None

    model_config = {"from_attributes": True}


class InviteIn(BaseModel):
    email: EmailStr
    role: str = Field(default="viewer", pattern=r"^(viewer|auditor|manager)$")


class RoleUpdateIn(BaseModel):
    role: str = Field(..., pattern=r"^(viewer|auditor|manager)$")


async def _assert_site_owner(site_id: int, user: User, db: AsyncSession) -> Site:
    result = await db.execute(select(Site).where(Site.id == site_id, Site.user_id == user.id))
    site = result.scalar_one_or_none()
    if not site:
        raise HTTPException(status_code=404, detail="Site non trouvé")
    return site


def _send_invite_email(email: str, site_name: str, site_url: str, role: str, token: str) -> None:
    try:
        from app.services.email_service import _send

        accept_url = f"https://cyberscanapp.com/cyberscan/collab/accept/{token}"
        role_label = ROLE_LABELS.get(role, role)
        html = f"""
        <div style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:32px;border-radius:12px;">
          <h2 style="color:#06b6d4;">Invitation à collaborer sur un audit</h2>
          <p>Vous avez été invité(e) à collaborer sur le site <strong>{site_url}</strong> avec le rôle <strong>{role_label}</strong>.</p>
          <a href="{accept_url}" style="display:inline-block;background:#06b6d4;color:#0f172a;padding:12px 24px;border-radius:8px;font-weight:bold;text-decoration:none;margin:16px 0;">
            Accepter l'invitation
          </a>
          <p style="color:#64748b;font-size:0.8em;">Ce lien est valable 7 jours.</p>
        </div>
        """
        plain = f"Vous êtes invité(e) à collaborer sur {site_url} (rôle : {role_label}).\nAcceptez : {accept_url}"
        _send(email, f"Invitation Rocher Cybersécurité — {site_name}", html, plain)
    except Exception as exc:
        logger.warning(f"Collab invitation email failed: {exc}")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/sites/{site_id}/collaborators", response_model=list[CollabOut])
async def list_collaborators(
    site_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_owner(site_id, current_user, db)
    result = await db.execute(select(SiteCollaborator).where(SiteCollaborator.site_id == site_id))
    return result.scalars().all()


@router.post("/sites/{site_id}/collaborators", response_model=CollabOut, status_code=201)
async def invite_collaborator(
    site_id: int,
    payload: InviteIn,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    site = await _assert_site_owner(site_id, current_user, db)

    # Check duplicate
    existing = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.site_id == site_id,
            SiteCollaborator.email == payload.email,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Cet email est déjà invité sur ce site")

    token = secrets.token_urlsafe(32)
    collab = SiteCollaborator(
        site_id=site_id,
        owner_user_id=current_user.id,
        email=payload.email,
        role=payload.role,
        status="pending",
        invite_token=token,
        invited_at=datetime.now(UTC),
    )
    db.add(collab)
    await db.commit()
    await db.refresh(collab)

    background_tasks.add_task(
        _send_invite_email, payload.email, site.name, site.url, payload.role, token
    )

    return collab


@router.put("/sites/{site_id}/collaborators/{collab_id}", response_model=CollabOut)
async def update_collaborator_role(
    site_id: int,
    collab_id: int,
    payload: RoleUpdateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_owner(site_id, current_user, db)
    result = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.id == collab_id,
            SiteCollaborator.site_id == site_id,
        )
    )
    collab = result.scalar_one_or_none()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaborateur non trouvé")

    collab.role = payload.role
    await db.commit()
    await db.refresh(collab)
    return collab


@router.delete("/sites/{site_id}/collaborators/{collab_id}", status_code=204)
async def remove_collaborator(
    site_id: int,
    collab_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _assert_site_owner(site_id, current_user, db)
    result = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.id == collab_id,
            SiteCollaborator.site_id == site_id,
        )
    )
    collab = result.scalar_one_or_none()
    if not collab:
        raise HTTPException(status_code=404, detail="Collaborateur non trouvé")
    await db.delete(collab)
    await db.commit()


@router.get("/accept/{token}", response_model=CollabOut)
async def accept_invite(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — accepts an invitation via the token link."""
    result = await db.execute(
        select(SiteCollaborator).where(SiteCollaborator.invite_token == token)
    )
    collab = result.scalar_one_or_none()
    if not collab:
        raise HTTPException(status_code=404, detail="Invitation introuvable ou expirée")
    if collab.status == "accepted":
        return collab

    collab.status = "accepted"
    collab.accepted_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(collab)
    return collab


@router.get("/my-invitations", response_model=list[CollabOut])
async def my_invitations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all sites the current user has been invited to collaborate on."""
    result = await db.execute(
        select(SiteCollaborator).where(
            SiteCollaborator.email == current_user.email,
            SiteCollaborator.status == "accepted",
        )
    )
    return result.scalars().all()
