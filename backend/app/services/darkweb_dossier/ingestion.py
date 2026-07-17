"""
ingestion.py — Background processing, CSV export, and monitoring alert email.
"""

from __future__ import annotations

import asyncio
import csv
import io
import json
from collections import Counter
from datetime import UTC, datetime, timedelta

from loguru import logger
from sqlalchemy import select

import app.core.database as _db_module
from app.models.darkweb_dossier import DarkwebDossier, DarkwebDossierTarget
from app.services.darkweb_service import check_email_breaches, enrich_breaches_from_catalog
from app.services.email_service import _send

from .enrichment import _build_catalog_index, _compute_severity

_BATCH_DELAY = 2.5  # seconds between API calls — LeakCheck public allows ~1 req/2–3s
_MONITOR_INTERVAL_DAYS = 30  # re-scan interval for monitored dossiers


async def process_dossier(dossier_id: int, api_key: str) -> None:
    """Process all targets for a dossier — runs in background with its own DB session."""
    async with _db_module.AsyncSessionLocal() as db:
        result = await db.execute(select(DarkwebDossier).where(DarkwebDossier.id == dossier_id))
        dossier = result.scalar_one_or_none()
        if not dossier:
            return

        dossier.status = "processing"
        dossier.started_at = datetime.now(UTC)
        dossier.checked_count = 0
        dossier.unverified_count = 0
        await db.commit()

        catalog = await _build_catalog_index(db)

        try:
            result = await db.execute(
                select(DarkwebDossierTarget).where(DarkwebDossierTarget.dossier_id == dossier_id)
            )
            targets = result.scalars().all()

            exposed = 0
            total_instances = 0
            unverified = 0

            for i, target in enumerate(targets):
                if i > 0:
                    await asyncio.sleep(_BATCH_DELAY)
                data = await asyncio.to_thread(check_email_breaches, target.email, api_key)
                breaches = enrich_breaches_from_catalog(data.get("breaches", []), catalog)
                count = data.get("total", 0)
                api_status = data.get("status", "unknown")
                api_error = data.get("error") or ""

                target.total_breaches = count
                target.breach_sources_json = json.dumps(breaches)
                target.checked_at = datetime.now(UTC)

                if api_status == "unknown":
                    is_rate_limited = any(
                        kw in api_error.lower() for kw in ("rate", "429", "retry", "throttl")
                    )
                    target.check_status = "rate_limited" if is_rate_limited else "api_error"
                    target.status = "error"
                    unverified += 1
                elif count > 0:
                    target.check_status = "exposed"
                    target.status = "exposed"
                    exposed += 1
                    total_instances += count
                else:
                    target.check_status = "verified_clean"
                    target.status = "clean"

                dossier.checked_count = i + 1
                dossier.unverified_count = unverified
                await db.commit()

            verified_total = len(targets) - unverified
            if verified_total > 0:
                heavy = sum(1 for t in targets if t.total_breaches >= 3)
                weighted = (exposed + heavy * 0.5) / (verified_total + heavy * 0.5)
                risk_score = min(100, round(weighted * 100))
            else:
                risk_score = 0

            all_sources: list[str] = []
            for target in targets:
                try:
                    src = json.loads(target.breach_sources_json or "[]")
                    all_sources.extend(b.get("name", "") for b in src if b.get("name"))
                except json.JSONDecodeError as exc:
                    logger.warning("breach_sources_json illisible pour une cible, ignore : {}", exc)
            top_sources = [{"name": n, "count": c} for n, c in Counter(all_sources).most_common(10)]

            severity_score = _compute_severity(targets)
            now = datetime.now(UTC)

            dossier.exposed_emails = exposed
            dossier.total_breach_instances = total_instances
            dossier.unverified_count = unverified
            dossier.risk_score = risk_score
            dossier.severity_score = severity_score
            dossier.top_sources_json = json.dumps(top_sources)
            dossier.status = "completed"
            dossier.finished_at = now
            dossier.last_monitored_at = now
            if dossier.monitor_active:
                dossier.next_monitor_at = now + timedelta(days=_MONITOR_INTERVAL_DAYS)
            await db.commit()

        except Exception as exc:
            dossier.status = "failed"
            dossier.error_message = str(exc)
            dossier.finished_at = datetime.now(UTC)
            await db.commit()


def export_dossier_csv(dossier: DarkwebDossier, targets: list[DarkwebDossierTarget]) -> bytes:
    """Build a UTF-8 BOM CSV with one row per target email."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Email",
            "Statut",
            "Vérification API",
            "Nb fuites",
            "Sources principales",
            "Types de données exposées",
            "Date vérification",
        ]
    )
    for t in targets:
        try:
            breaches = json.loads(t.breach_sources_json or "[]")
        except json.JSONDecodeError:
            breaches = []
        sources = ", ".join(b.get("name", "") for b in breaches[:5])
        data_classes = ", ".join(
            dc
            for b in breaches
            for dc in b.get("data_classes", [])
            if dc not in ("Email addresses",)
        )
        checked = t.checked_at.strftime("%Y-%m-%d") if t.checked_at else ""
        writer.writerow(
            [
                t.email,
                t.status,
                t.check_status,
                t.total_breaches,
                sources,
                data_classes,
                checked,
            ]
        )
    return ("﻿" + output.getvalue()).encode("utf-8")


def send_monitoring_alert(
    to_email: str,
    company_name: str,
    domain: str,
    exposed_count: int,
    new_exposed: list[str],
    dashboard_url: str,
) -> None:
    """Send an alert email when monitoring detects new exposed accounts."""
    new_list_html = "".join(f"<li style='color:#fca5a5'>{e}</li>" for e in new_exposed[:10])
    more = (
        f"<p style='color:#94a3b8;font-size:13px'>+ {len(new_exposed) - 10} autres</p>"
        if len(new_exposed) > 10
        else ""
    )

    subject = f"[Rocher Cybersécurité] ⚠️ Dark Web — Nouvelles fuites détectées pour {domain}"
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#ef444422,#ef444411);padding:32px 40px;border-bottom:2px solid #ef4444;text-align:center;">
<p style="margin:0 0 6px;color:#ef4444;font-size:12px;font-weight:800;letter-spacing:2px;">ALERTE DARK WEB</p>
<h1 style="margin:0;color:#f8fafc;font-size:22px;">Nouvelles fuites détectées</h1>
</td></tr>
<tr><td style="padding:32px 40px;">
<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">
Le monitoring Dark Web de <strong style="color:#f8fafc;">{company_name}</strong> ({domain}) a détecté
<strong style="color:#ef4444;font-size:18px;"> {exposed_count} compte(s) exposé(s)</strong> lors du rescan mensuel.
</p>
<p style="color:#94a3b8;font-size:13px;margin:0 0 8px;font-weight:700;letter-spacing:1px;">NOUVEAUX COMPTES DÉTECTÉS :</p>
<ul style="margin:0 0 24px;padding-left:20px;">{new_list_html}</ul>
{more}
<a href="{dashboard_url}" style="display:inline-block;background:#ef4444;color:white;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px;">
  Voir le rapport complet
</a>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #1e293b;text-align:center;">
<p style="margin:0;color:#475569;font-size:12px;">Rocher Cybersécurité — Surveillance Dark Web B2B</p>
</td></tr>
</table></td></tr></table>
</body></html>"""
    plain = f"[ALERTE DARK WEB] {company_name} ({domain}) — {exposed_count} compte(s) exposé(s) détecté(s).\n\nConsultez le rapport : {dashboard_url}"
    try:
        _send(to_email, subject, html, plain)
    except Exception as exc:
        logger.warning(f"Dark web monitoring alert email failed for {to_email}: {exc}")


# Backward-compatible alias used by scheduler.py
send_darkweb_alert_email = send_monitoring_alert
