"""Job de rétention / purge RGPD (Art.5-1-e — limitation de conservation).

Exécuté chaque nuit à 05:00 UTC. Supprime les données à caractère personnel
dont la finalité est expirée :

- **public_scans** : leads anonymes du scan gratuit (email + ip_hash salé +
  results_json). Aucun rattachement compte, finalité = livraison ponctuelle du
  rapport → purge dure après `PUBLIC_SCAN_RETENTION_DAYS` jours.
- **fichiers_deposes** ORPHELINS : fichiers stockés que plus aucun livrable ne
  référence. Le dépôt rend une clé, un second appel crée le livrable ; si ce
  second appel n'arrive jamais, le fichier reste sur S3 sans finalité. Purge
  après `DELAI_ORPHELIN_JOURS` jours — délai de grâce, le temps que le flux
  normal se termine. Contrairement aux deux autres, cette purge efface AUSSI
  l'objet stocké, pas seulement la ligne.
- **darkweb_dossiers** NON surveillés : dossiers Dark Web B2B (emails de salariés
  exposés) dont la surveillance mensuelle est désactivée (`monitor_active=False`).
  Un dossier surveillé a une finalité ACTIVE (alerte sur nouvelles fuites) et est
  conservé tant que la surveillance tourne ; un dossier ponctuel est purgé après
  `DARKWEB_DOSSIER_RETENTION_DAYS` jours. La suppression cascade sur
  `darkweb_dossier_targets` via la FK `ondelete=CASCADE`.

Purge = suppression définitive (pas d'anonymisation partielle) : ces lignes ne
portent pas de valeur analytique agrégée justifiant une conservation anonymisée.
"""

from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.models.darkweb_dossier import DarkwebDossier
from app.models.public_scan import PublicScan
from app.services import depot_service

PUBLIC_SCAN_RETENTION_DAYS = 90
DARKWEB_DOSSIER_RETENTION_DAYS = 90


async def purge_expired_data(db: AsyncSession, now: datetime) -> dict[str, int]:
    """Supprime les données expirées et renvoie le nombre de lignes purgées par table.

    Isolé de l'ordonnanceur pour être testable avec une date `now` injectée.
    """
    public_cutoff = now - timedelta(days=PUBLIC_SCAN_RETENTION_DAYS)
    darkweb_cutoff = now - timedelta(days=DARKWEB_DOSSIER_RETENTION_DAYS)

    public_result = await db.execute(
        delete(PublicScan).where(PublicScan.created_at < public_cutoff)
    )
    # Seuls les dossiers NON surveillés sont purgés : un dossier surveillé garde une
    # finalité active (alerte mensuelle) tant que monitor_active est vrai.
    darkweb_result = await db.execute(
        delete(DarkwebDossier).where(
            DarkwebDossier.monitor_active.is_(False),
            DarkwebDossier.created_at < darkweb_cutoff,
        )
    )
    await db.commit()

    # Après le commit : cette purge-ci touche au stockage objet, pas seulement à
    # la base. La garder à part évite qu'un échec S3 fasse retomber les deux
    # suppressions ci-dessus, qui n'ont rien à voir avec elle.
    orphelins = await depot_service.purger_orphelins(db, now)

    return {
        "public_scans": public_result.rowcount or 0,
        "darkweb_dossiers": darkweb_result.rowcount or 0,
        "fichiers_orphelins": orphelins,
    }


async def _run_data_retention_purge() -> None:
    """Job nocturne (05:00 UTC) : purge les PII expirées (public_scans + Dark Web)."""
    async with AsyncSessionLocal() as db:
        counts = await purge_expired_data(db, datetime.now(UTC))
    if any(counts.values()):
        logger.info(
            "Purge rétention RGPD : {} public_scans, {} darkweb_dossiers, "
            "{} fichiers orphelins supprimés",
            counts["public_scans"],
            counts["darkweb_dossiers"],
            counts["fichiers_orphelins"],
        )
