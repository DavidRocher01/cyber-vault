"""Service d'accès aux clients RSSI (CRUD, sites liés, agrégats, portail).

L'endpoint garde le façonnage HTTP (RssiClientOut / RssiSiteOut), la génération
et le hachage des tokens d'invitation et l'envoi d'e-mail ; ce service porte les
requêtes et les frontières de transaction. Les fonctions reçoivent des valeurs
déjà préparées (dicts de champs, hash de token), jamais un schéma HTTP.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.models.password_reset_token import PasswordResetToken
from app.models.rssi_client import RssiClient
from app.models.scan import Scan
from app.models.site import Site
from app.models.user import User

# Ordre de gravité pour agréger le pire statut d'un ensemble de scans.
STATUS_ORDER = {"CRITICAL": 0, "WARNING": 1, "OK": 2}


async def get_client_for_consultant(
    db: AsyncSession, client_id: int, consultant_id: int
) -> RssiClient | None:
    """Retourne le client s'il appartient au consultant, sinon None."""
    result = await db.execute(
        select(RssiClient).where(
            RssiClient.id == client_id,
            RssiClient.consultant_user_id == consultant_id,
        )
    )
    return result.scalar_one_or_none()


# ── CRUD client ────────────────────────────────────────────────────────────────


async def list_clients_for_consultant(db: AsyncSession, consultant_id: int) -> list[RssiClient]:
    """Clients du consultant, du plus récent au plus ancien."""
    result = await db.execute(
        select(RssiClient)
        .where(RssiClient.consultant_user_id == consultant_id)
        .order_by(RssiClient.created_at.desc())
    )
    return list(result.scalars().all())


async def create_client(db: AsyncSession, *, consultant_user_id: int, values: dict) -> RssiClient:
    """Crée un client RSSI pour le consultant (dict de champs modèle)."""
    client = RssiClient(consultant_user_id=consultant_user_id, **values)
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client


# Statuts qui marquent la FIN de la prestation. `active` est le seul qui ne
# l'est pas — un client en pause reste un client suivi.
STATUTS_MISSION_CLOSE = ("inactive", "churned")


async def update_client(db: AsyncSession, client: RssiClient, values: dict) -> RssiClient:
    """Applique un patch partiel au client, met à jour updated_at et la clôture.

    LA DATE DE CLOTURE SE POSE ICI, et nulle part ailleurs : c'est le seul point
    de passage des modifications de client. Elle commande la rétention des
    documents que le client a remis — art. 28-3-g du RGPD, la prestation
    terminée, le sous-traitant efface ou restitue.

    Elle est POSEE au passage en `inactive` / `churned`, et EFFACEE au retour en
    `active`. Un client repris ne doit pas voir ses documents purgés sur la foi
    d'une interruption passée ; et la date ne se repousse pas si le statut ne
    change pas, sans quoi une simple correction d'adresse reporterait
    l'échéance.
    """
    ancien_statut = client.status
    for field, value in values.items():
        setattr(client, field, value)

    if client.status in STATUTS_MISSION_CLOSE and ancien_statut not in STATUTS_MISSION_CLOSE:
        client.cloture_le = datetime.now(UTC)
    elif client.status not in STATUTS_MISSION_CLOSE:
        client.cloture_le = None

    client.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(client)
    return client


async def delete_client(db: AsyncSession, client: RssiClient) -> None:
    """Détache les sites du client puis supprime le client."""
    sites_result = await db.execute(select(Site).where(Site.rssi_client_id == client.id))
    for site in sites_result.scalars().all():
        site.rssi_client_id = None
    await db.delete(client)
    await db.commit()


# ── Sites & scans ────────────────────────────────────────────────────────────


async def latest_done_scans_by_site(db: AsyncSession, site_ids: list[int]) -> dict[int, Scan]:
    """Dernier scan 'done' par site pour la liste fournie."""
    latest: dict[int, Scan] = {}
    if not site_ids:
        return latest
    result = await db.execute(
        select(Scan)
        .where(Scan.site_id.in_(site_ids), Scan.status == "done")
        .order_by(Scan.finished_at.desc())
    )
    for scan in result.scalars().all():
        if scan.site_id not in latest:
            latest[scan.site_id] = scan
    return latest


async def compute_client_aggregates(
    db: AsyncSession, client_ids: list[int], user_id: int
) -> dict[int, tuple[int, str | None, datetime | None]]:
    """Retourne {client_id: (nb_sites, pire_statut, date_dernier_scan)} par client."""
    if not client_ids:
        return {}

    sites_result = await db.execute(
        select(Site).where(
            Site.user_id == user_id,
            Site.rssi_client_id.in_(client_ids),
            Site.is_active == True,  # noqa: E712
        )
    )
    sites = sites_result.scalars().all()
    sites_by_client: dict[int, list[Site]] = {}
    for s in sites:
        sites_by_client.setdefault(s.rssi_client_id, []).append(s)

    latest_scans = await latest_done_scans_by_site(db, [s.id for s in sites])

    aggregates: dict[int, tuple[int, str | None, datetime | None]] = {}
    for cid in client_ids:
        client_sites = sites_by_client.get(cid, [])
        client_scans = [latest_scans[s.id] for s in client_sites if s.id in latest_scans]

        worst: str | None = None
        if client_scans:
            statuses = [sc.overall_status for sc in client_scans if sc.overall_status]
            if statuses:
                worst = sorted(statuses, key=lambda x: STATUS_ORDER.get(x, 99))[0]

        last_scan_at = max((sc.finished_at for sc in client_scans if sc.finished_at), default=None)
        aggregates[cid] = (len(client_sites), worst, last_scan_at)

    return aggregates


async def list_active_sites_for_client(
    db: AsyncSession, user_id: int, client_id: int
) -> list[Site]:
    """Sites actifs de l'utilisateur liés à ce client, du plus récent au plus ancien."""
    result = await db.execute(
        select(Site)
        .where(
            Site.user_id == user_id,
            Site.rssi_client_id == client_id,
            Site.is_active == True,  # noqa: E712
        )
        .order_by(Site.created_at.desc())
    )
    return list(result.scalars().all())


async def list_unlinked_sites(db: AsyncSession, user_id: int) -> list[Site]:
    """Sites actifs de l'utilisateur non rattachés à un client RSSI."""
    result = await db.execute(
        select(Site)
        .where(
            Site.user_id == user_id,
            Site.is_active == True,  # noqa: E712
            Site.rssi_client_id.is_(None),
        )
        .order_by(Site.name)
    )
    return list(result.scalars().all())


async def get_active_site(db: AsyncSession, site_id: int, user_id: int) -> Site | None:
    """Site actif de l'utilisateur par identifiant, sinon None."""
    result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.user_id == user_id,
            Site.is_active == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def link_site(db: AsyncSession, site: Site, client_id: int) -> Site:
    """Rattache un site à un client RSSI."""
    site.rssi_client_id = client_id
    await db.commit()
    await db.refresh(site)
    return site


async def latest_done_scan_for_site(db: AsyncSession, site_id: int) -> Scan | None:
    """Dernier scan 'done' d'un site, sinon None."""
    result = await db.execute(
        select(Scan)
        .where(Scan.site_id == site_id, Scan.status == "done")
        .order_by(Scan.finished_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_linked_site(
    db: AsyncSession, site_id: int, user_id: int, client_id: int
) -> Site | None:
    """Site de l'utilisateur rattaché à ce client précis, sinon None."""
    result = await db.execute(
        select(Site).where(
            Site.id == site_id,
            Site.user_id == user_id,
            Site.rssi_client_id == client_id,
        )
    )
    return result.scalar_one_or_none()


async def unlink_site(db: AsyncSession, site: Site) -> None:
    """Retire le lien entre un site et son client RSSI (le site n'est pas supprimé)."""
    site.rssi_client_id = None
    await db.commit()


# ── Invitation au portail client ─────────────────────────────────────────────


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Utilisateur par email, sinon None."""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def create_portal_user(db: AsyncSession, *, email: str, hashed_password: str) -> User:
    """Crée un compte client de portail (flush pour obtenir l'id, sans commit)."""
    user = User(email=email, hashed_password=hashed_password, is_active=True)
    db.add(user)
    await db.flush()
    return user


async def get_other_client_for_user(
    db: AsyncSession, *, user_id: int, exclude_client_id: int
) -> RssiClient | None:
    """Autre client déjà rattaché à ce compte de portail, sinon None (unicité)."""
    result = await db.execute(
        select(RssiClient).where(
            RssiClient.client_user_id == user_id,
            RssiClient.id != exclude_client_id,
        )
    )
    return result.scalar_one_or_none()


async def link_client_and_add_reset_token(
    db: AsyncSession,
    *,
    client: RssiClient,
    user_id: int,
    token_hash: str,
    expires_at: datetime,
) -> None:
    """Rattache le compte au client et crée le token de définition de mot de passe."""
    client.client_user_id = user_id
    db.add(PasswordResetToken(user_id=user_id, token=token_hash, expires_at=expires_at))
    await db.commit()


# ── Sensibilisation (organisation de formation liée) ─────────────────────────


async def count_learners(db: AsyncSession, org_id: int) -> int:
    """Nombre d'apprenants d'une organisation de sensibilisation."""
    result = await db.execute(
        select(func.count(AwarenessLearner.id)).where(AwarenessLearner.organization_id == org_id)
    )
    return result.scalar() or 0


async def get_awareness_org(db: AsyncSession, org_id: int) -> AwarenessOrganization | None:
    """Organisation de sensibilisation par identifiant, sinon None."""
    result = await db.execute(
        select(AwarenessOrganization).where(AwarenessOrganization.id == org_id)
    )
    return result.scalar_one_or_none()


async def create_awareness_org_for_client(
    db: AsyncSession, *, client: RssiClient, owner_user_id: int, name: str, max_learners: int
) -> AwarenessOrganization:
    """Crée l'organisation de sensibilisation et la rattache au client RSSI."""
    org = AwarenessOrganization(owner_user_id=owner_user_id, name=name, max_learners=max_learners)
    db.add(org)
    await db.flush()
    client.awareness_organization_id = org.id
    await db.commit()
    return org
