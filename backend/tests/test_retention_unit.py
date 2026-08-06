"""Tests unitaires du job de rétention / purge RGPD (audit #13).

Vérifie que `purge_expired_data` :
- purge les public_scans plus vieux que la rétention (leads anonymes),
- purge les dossiers Dark Web NON surveillés et expirés (+ cascade sur les cibles),
- CONSERVE les dossiers surveillés (finalité active) et tout ce qui est récent.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
from app.models.public_scan import PublicScan
from app.models.user import User
from app.services.scheduler.retention import (
    DARKWEB_DOSSIER_RETENTION_DAYS,
    PUBLIC_SCAN_RETENTION_DAYS,
    purge_expired_data,
)

pytestmark = pytest.mark.asyncio

NOW = datetime(2026, 7, 29, 5, 0, tzinfo=UTC)


async def _count(db, model) -> int:
    return (await db.execute(select(func.count()).select_from(model))).scalar_one()


async def test_purge_expired_data_removes_only_expired_and_unmonitored(db_session):
    old = NOW - timedelta(days=PUBLIC_SCAN_RETENTION_DAYS + 5)
    recent = NOW - timedelta(days=10)

    # public_scans : un vieux (purgé), un récent (conservé)
    db_session.add(PublicScan(target_url="https://old.example", created_at=old))
    db_session.add(PublicScan(target_url="https://recent.example", created_at=recent))

    # Un utilisateur porteur des dossiers Dark Web
    user = User(email="ret@test.com", hashed_password="x")
    db_session.add(user)
    await db_session.flush()

    # Dossier NON surveillé + expiré → purgé (avec sa cible en cascade)
    dossier_purge = DarkwebDossier(
        user_id=user.id,
        company_name="Purge SA",
        domain="purge.example",
        monitor_active=False,
        created_at=NOW - timedelta(days=DARKWEB_DOSSIER_RETENTION_DAYS + 5),
    )
    db_session.add(dossier_purge)
    await db_session.flush()
    db_session.add(DarkwebDossierTarget(dossier_id=dossier_purge.id, email="victim@purge.example"))

    # Dossier SURVEILLÉ + expiré → conservé (finalité active)
    dossier_monitored = DarkwebDossier(
        user_id=user.id,
        company_name="Monitored SA",
        domain="monitored.example",
        monitor_active=True,
        created_at=NOW - timedelta(days=DARKWEB_DOSSIER_RETENTION_DAYS + 5),
    )
    db_session.add(dossier_monitored)

    # Dossier NON surveillé mais récent → conservé
    dossier_recent = DarkwebDossier(
        user_id=user.id,
        company_name="Recent SA",
        domain="recent.example",
        monitor_active=False,
        created_at=NOW - timedelta(days=10),
    )
    db_session.add(dossier_recent)
    await db_session.commit()

    counts = await purge_expired_data(db_session, NOW)

    assert counts == {
        "public_scans": 1,
        "darkweb_dossiers": 1,
        "fichiers_orphelins": 0,
        "documents_clients": 0,
    }

    # public_scans : seul le récent survit
    remaining_scans = (await db_session.execute(select(PublicScan.target_url))).scalars().all()
    assert remaining_scans == ["https://recent.example"]

    # darkweb_dossiers : le surveillé + le récent survivent (2)
    assert await _count(db_session, DarkwebDossier) == 2
    remaining_domains = set(
        (await db_session.execute(select(DarkwebDossier.domain))).scalars().all()
    )
    assert remaining_domains == {"monitored.example", "recent.example"}

    # La cible du dossier purgé a bien cascadé (0 cible restante)
    assert await _count(db_session, DarkwebDossierTarget) == 0


async def test_purge_expired_data_noop_when_nothing_expired(db_session):
    db_session.add(
        PublicScan(target_url="https://fresh.example", created_at=NOW - timedelta(days=1))
    )
    await db_session.commit()

    counts = await purge_expired_data(db_session, NOW)

    assert counts == {
        "public_scans": 0,
        "darkweb_dossiers": 0,
        "fichiers_orphelins": 0,
        "documents_clients": 0,
    }
    assert await _count(db_session, PublicScan) == 1
