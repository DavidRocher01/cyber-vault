"""
enrichment.py — Severity scoring, breach catalog helpers, and recommendations.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.breach_catalog import BreachCatalogEntry
from app.services.darkweb_service import fetch_hibp_breach_catalog

# Severity weights by data class keyword (higher = more dangerous)
_SEVERITY_WEIGHTS: dict[str, int] = {
    "password": 4,
    "mot de passe": 4,
    "credit card": 5,
    "carte": 5,
    "financial": 5,
    "bank": 5,
    "social security": 5,
    "phone": 2,
    "address": 2,
    "username": 2,
    "name": 1,
    "email": 1,
}


def _compute_severity(targets: list) -> int:
    """Return a 0-100 severity score weighted by breach data_classes."""
    total_weight = 0
    max_possible = 0
    for t in targets:
        try:
            breaches = json.loads(t.breach_sources_json or "[]")
        except json.JSONDecodeError:
            continue
        for b in breaches:
            classes = [c.lower() for c in b.get("data_classes", [])]
            weight = 1
            for dc in classes:
                for keyword, w in _SEVERITY_WEIGHTS.items():
                    if keyword in dc:
                        weight = max(weight, w)
            total_weight += weight
            max_possible += max(_SEVERITY_WEIGHTS.values())
    if max_possible == 0:
        return 0
    return min(100, round(total_weight / max_possible * 100))


async def sync_breach_catalog(db: AsyncSession) -> int:
    """Fetch HIBP public breach list and upsert into local breach_catalog table."""
    from app.models.breach_catalog import BreachCatalogEntry

    raw = await asyncio.to_thread(fetch_hibp_breach_catalog)
    if not raw:
        return 0
    upserted = 0
    for entry in raw:
        name = entry.get("Name", "")
        if not name:
            continue
        result = await db.execute(select(BreachCatalogEntry).where(BreachCatalogEntry.name == name))
        existing = result.scalar_one_or_none()
        data_classes = json.dumps(entry.get("DataClasses", []))
        if existing:
            existing.title = entry.get("Title", "")
            existing.domain = entry.get("Domain", "")
            existing.breach_date = entry.get("BreachDate", "")
            existing.added_date = entry.get("AddedDate", "")
            existing.pwn_count = entry.get("PwnCount", 0)
            existing.description = entry.get("Description", "")
            existing.data_classes_json = data_classes
            existing.is_verified = entry.get("IsVerified", False)
            existing.is_sensitive = entry.get("IsSensitive", False)
            existing.is_fabricated = entry.get("IsFabricated", False)
            existing.is_spam_list = entry.get("IsSpamList", False)
            existing.updated_at = datetime.now(UTC)
        else:
            db.add(
                BreachCatalogEntry(
                    name=name,
                    title=entry.get("Title", ""),
                    domain=entry.get("Domain", ""),
                    breach_date=entry.get("BreachDate", ""),
                    added_date=entry.get("AddedDate", ""),
                    pwn_count=entry.get("PwnCount", 0),
                    description=entry.get("Description", ""),
                    data_classes_json=data_classes,
                    is_verified=entry.get("IsVerified", False),
                    is_sensitive=entry.get("IsSensitive", False),
                    is_fabricated=entry.get("IsFabricated", False),
                    is_spam_list=entry.get("IsSpamList", False),
                )
            )
        upserted += 1
    await db.commit()
    return upserted


async def _build_catalog_index(db: AsyncSession) -> dict[str, dict]:
    """Return a {name.lower(): entry_dict} index from local catalog."""
    result = await db.execute(select(BreachCatalogEntry))
    entries = result.scalars().all()
    index: dict[str, dict] = {}
    for e in entries:
        try:
            dc = json.loads(e.data_classes_json or "[]")
        except json.JSONDecodeError:
            dc = []
        index[e.name.lower()] = {
            "domain": e.domain or "",
            "breach_date": e.breach_date or "",
            "pwn_count": e.pwn_count,
            "data_classes": dc,
            "is_sensitive": e.is_sensitive,
            "is_verified": e.is_verified,
        }
    return index


def _build_recommendations(dossier, targets: list) -> list[tuple[str, str]]:
    """Build context-aware recommendations based on actual findings."""

    exposed_targets = [t for t in targets if t.status == "exposed"]
    unverified_targets = [t for t in targets if t.status == "error"]

    all_classes: list[str] = []
    for t in exposed_targets:
        try:
            breaches = json.loads(t.breach_sources_json or "[]")
        except json.JSONDecodeError:
            continue
        for b in breaches:
            all_classes.extend(c.lower() for c in b.get("data_classes", []))

    has_password = any("password" in c or "mot de passe" in c for c in all_classes)
    has_financial = any(
        k in c for c in all_classes for k in ("credit", "financial", "bank", "carte", "payment")
    )
    has_sensitive = any(
        k in c
        for c in all_classes
        for k in ("social security", "health", "medical", "ssn", "passport")
    )

    recs: list[tuple[str, str]] = []

    if exposed_targets:
        recs.append(
            (
                "Réinitialisation des mots de passe exposés",
                f"Forcer un changement de mot de passe pour les {len(exposed_targets)} compte(s) "
                "identifié(s) comme exposé(s). Prioriser ceux avec 3 fuites ou plus et vérifier "
                "toute réutilisation sur d'autres services.",
            )
        )

    if has_password or (exposed_targets and not all_classes):
        recs.append(
            (
                "Activation de l'authentification multi-facteur (MFA)",
                "Déployer le MFA sur tous les accès critiques (messagerie, VPN, outils métiers). "
                "Un mot de passe volé seul ne suffit plus à compromettre un compte protégé par MFA.",
            )
        )

    if has_financial:
        recs.append(
            (
                "Alerte financière — vérification des accès bancaires",
                "Des données financières (cartes, coordonnées bancaires) ont été détectées dans les fuites. "
                "Vérifier les accès aux outils bancaires et comptables, et signaler aux établissements concernés.",
            )
        )

    if has_sensitive:
        recs.append(
            (
                "Données personnelles sensibles — notification RGPD",
                "Des données personnelles hautement sensibles ont été trouvées dans les fuites. "
                "Informer les personnes concernées et envisager une notification à la CNIL si requis.",
            )
        )

    if unverified_targets:
        recs.append(
            (
                f"Vérification incomplète — {len(unverified_targets)} adresse(s) non analysée(s)",
                "Certaines adresses n'ont pas pu être vérifiées en raison de limitations des APIs (rate limit). "
                "Relancer un rescan pour obtenir des résultats complets avant de conclure sur l'exposition réelle.",
            )
        )

    risk_score = dossier.risk_score or 0
    if risk_score >= 50:
        surveillance_body = (
            f"Score de risque élevé ({risk_score}%) — une surveillance rapprochée est essentielle. "
            "Activer le monitoring mensuel automatique et planifier un rescan dans 30 jours."
        )
    else:
        surveillance_body = (
            "Programmer une nouvelle analyse dans 30 jours pour détecter d'éventuelles nouvelles fuites. "
            "Activer le monitoring mensuel depuis le tableau de bord pour être alerté immédiatement."
        )
    recs.append(("Surveillance continue", surveillance_body))

    if len(recs) < 4:
        recs.append(
            (
                "Formation et sensibilisation des équipes",
                "Intégrer les résultats de cette analyse dans le programme de sensibilisation à la cybersécurité. "
                "Les collaborateurs exposés devraient suivre une formation sur la gestion des mots de passe.",
            )
        )

    return recs[:6]
