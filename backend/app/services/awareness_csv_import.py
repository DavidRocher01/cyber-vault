"""
CSV import for awareness learners.

Expected CSV columns (order-insensitive, case-insensitive):
  email (required), first_name, last_name, department, job_title, preferred_language

Behaviour: upsert on (organization_id, email) — creates if new, updates if existing.
"""

from __future__ import annotations

import csv
import io

from pydantic import EmailStr, ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awareness_learner import AwarenessLearner
from app.models.awareness_organization import AwarenessOrganization
from app.schemas.awareness import CsvImportResult
from app.services.awareness_learner_service import count_active_learners

_REQUIRED = {"email"}
_OPTIONAL = {"first_name", "last_name", "department", "job_title", "preferred_language"}
_ALL_COLUMNS = _REQUIRED | _OPTIONAL
_MAX_ROWS = 500


def _normalise_headers(row: dict) -> dict:
    return {k.strip().lower(): v.strip() for k, v in row.items()}


async def import_learners_from_csv(
    db: AsyncSession,
    organization_id: int,
    csv_bytes: bytes,
    auto_activate: bool = True,
) -> CsvImportResult:
    """Importe des apprenants depuis un CSV, dans la limite du quota.

    Le quota etait verifie a la creation unitaire d'un apprenant (endpoint
    learners) mais PAS ici : l'import en masse le contournait entierement. Une
    organisation vendue pour 10 apprenants pouvait en recevoir 500 par CSV.

    Les lignes au-dela du quota sont comptees dans `skipped` avec une erreur
    explicite, plutot que de rejeter tout le fichier : l'utilisateur garde ce qui
    tient et sait exactement ce qui manque.
    """
    result = CsvImportResult()

    org = await db.get(AwarenessOrganization, organization_id)
    quota = org.max_learners if org else 0
    actifs = await count_active_learners(db, organization_id)
    restants = max(quota - actifs, 0)

    try:
        text = csv_bytes.decode("utf-8-sig")  # strip BOM if present
    except UnicodeDecodeError:
        text = csv_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        result.errors.append("Fichier CSV vide ou sans en-têtes.")
        return result

    headers = {h.strip().lower() for h in reader.fieldnames}
    if "email" not in headers:
        result.errors.append("Colonne 'email' obligatoire manquante.")
        return result

    rows = list(reader)
    if len(rows) > _MAX_ROWS:
        result.errors.append(f"Limite de {_MAX_ROWS} lignes dépassée ({len(rows)} reçues).")
        return result

    for line_num, raw_row in enumerate(rows, start=2):
        row = _normalise_headers(raw_row)
        email = row.get("email", "").strip().lower()

        if not email:
            result.skipped += 1
            continue

        # Validate email format
        try:
            EmailStr._validate(email)  # type: ignore[attr-defined]
        except (ValueError, ValidationError):
            result.errors.append(f"Ligne {line_num} : email invalide '{email}'")
            result.skipped += 1
            continue

        # Upsert learner
        existing = (
            await db.execute(
                select(AwarenessLearner).where(
                    AwarenessLearner.organization_id == organization_id,
                    AwarenessLearner.email == email,
                )
            )
        ).scalar_one_or_none()

        if existing:
            # Update mutable fields only if provided in CSV
            for field in _OPTIONAL:
                val = row.get(field)
                if val:
                    setattr(existing, field, val)
            if auto_activate:
                existing.is_active = True
            result.updated += 1
        else:
            if restants <= 0:
                result.skipped += 1
                result.errors.append(
                    f"{email} : quota atteint ({quota} apprenants max pour cette organisation)."
                )
                continue
            restants -= 1
            learner = AwarenessLearner(
                organization_id=organization_id,
                email=email,
                first_name=row.get("first_name") or None,
                last_name=row.get("last_name") or None,
                department=row.get("department") or None,
                job_title=row.get("job_title") or None,
                preferred_language=row.get("preferred_language") or "fr",
                is_active=auto_activate,
            )
            db.add(learner)
            result.created += 1

    await db.commit()
    return result
