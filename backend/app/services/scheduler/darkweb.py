"""Job monitoring dark web — re-scanne quotidiennement (03:00 UTC) les dossiers
surveillés dont next_monitor_at est échu et alerte sur les nouvelles expositions."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal

# Palier minimum requis pour la surveillance recurrente (Pro), aligne sur
# `_TIER_DARKWEB` de l'endpoint darkweb_dossier.
_TIER_MONITORING = 3


async def _run_darkweb_monitoring() -> None:
    """Daily job (03:00 UTC) : re-scanne les dossiers surveilles dont next_monitor_at
    est echu (cadence effective ~mensuelle par dossier) et alerte sur les nouvelles
    expositions."""
    from app.core.config import settings
    from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
    from app.models.user import User
    from app.services.darkweb_dossier_service import (
        process_dossier,
        send_darkweb_alert_email,
    )
    from app.services.subscription_service import get_active_tier

    async with AsyncSessionLocal() as db:
        now = datetime.now(UTC)
        result = await db.execute(
            select(DarkwebDossier).where(
                DarkwebDossier.monitor_active == True,  # noqa: E712
                DarkwebDossier.status == "completed",
                DarkwebDossier.next_monitor_at <= now,
            )
        )
        dossiers = result.scalars().all()

        # `monitor_active` reste vrai apres une retrogradation : l'abonne l'a pose
        # du temps ou il etait Pro, et rien ne l'efface. Sans ce filtre, un compte
        # redescendu en Gratuit continuait d'etre re-scanne et alerte chaque mois,
        # indefiniment et aux frais des appels HIBP. On verifie donc le palier au
        # moment de l'execution, pas seulement a l'activation.
        autorises = []
        for d in dossiers:
            if await get_active_tier(db, d.user_id) >= _TIER_MONITORING:
                autorises.append(d)
        dossiers = autorises

    for d in dossiers:
        # Snapshot exposed emails before re-scan
        async with AsyncSessionLocal() as db:
            prev_result = await db.execute(
                select(DarkwebDossierTarget).where(
                    DarkwebDossierTarget.dossier_id == d.id,
                    DarkwebDossierTarget.status == "exposed",
                )
            )
            prev_exposed = {t.email for t in prev_result.scalars().all()}

        # Re-scan NON destructif : process_dossier re-scanne toutes les cibles en
        # place, recalcule les agregats a la fin, et en cas d'echec passe le dossier
        # en "failed" SANS effacer les donnees precedentes (il attrape ses propres
        # exceptions, donc n'interrompt pas la boucle). On ne reinitialise donc plus
        # le dossier a "pending" avant le scan (ancienne fenetre de perte de donnees
        # si le re-scan echouait, et reset de toute facon redondant).
        await process_dossier(d.id, settings.HIBP_API_KEY)

        # Check for new exposures and alert
        async with AsyncSessionLocal() as db:
            new_result = await db.execute(
                select(DarkwebDossierTarget).where(
                    DarkwebDossierTarget.dossier_id == d.id,
                    DarkwebDossierTarget.status == "exposed",
                )
            )
            new_exposed = [
                t.email for t in new_result.scalars().all() if t.email not in prev_exposed
            ]

            user_result = await db.execute(select(User).where(User.id == d.user_id))
            user = user_result.scalar_one_or_none()

        if new_exposed and user:
            dashboard_url = f"{settings.FRONTEND_URL}/darkweb-dossier/{d.id}"
            send_darkweb_alert_email(
                to_email=user.email,
                company_name=d.company_name,
                domain=d.domain,
                exposed_count=len(new_exposed),
                new_exposed=new_exposed,
                dashboard_url=dashboard_url,
            )
