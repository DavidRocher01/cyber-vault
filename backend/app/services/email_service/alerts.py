"""Emails d'alerte : scan URL, campagne phishing, contact, réservations."""

from loguru import logger

from app.core.config import settings

from .base import _send


def send_url_scan_alert(
    to_email: str,
    scanned_url: str,
    verdict: str,
    threat_score: int,
    threat_type: str | None,
    findings: list[dict],
    dashboard_url: str,
) -> None:
    verdict_emoji = {"safe": "✅", "suspicious": "⚠️", "malicious": "🚨"}.get(verdict, "📋")
    verdict_fr = {
        "safe": "Sûr",
        "suspicious": "Suspect",
        "malicious": "Malveillant",
    }.get(verdict, verdict)
    threat_fr = {
        "phishing": "Phishing",
        "malware": "Malware / Script malveillant",
        "redirect": "Redirection suspecte",
        "tracker": "Tracker / Iframe externe",
        "malicious_domain": "Domaine malveillant",
    }.get(threat_type or "", "Inconnu")

    findings_lines = ""
    for f in findings[:8]:
        sev = {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(f.get("severity", ""), "⚪")
        findings_lines += f"  {sev} {f.get('detail', '')}\n"

    plain = f"""Bonjour,

L'analyse de l'URL suivante vient de se terminer :

  URL analysée : {scanned_url}
  Verdict      : {verdict_fr} {verdict_emoji}
  Score        : {threat_score}/100
  Type         : {threat_fr if threat_type else '—'}

━━━ Comportements détectés ━━━
{findings_lines if findings_lines else '  Aucun comportement suspect détecté.'}

━━━ Actions rapides ━━━
  Accéder au rapport complet : {dashboard_url}

---
Rocher Cybersécurité — Cybersécurité as a Service
"""
    subject = (
        f"[ScanURL] {verdict_emoji} {verdict_fr} — Score {threat_score}/100 — {scanned_url[:60]}"
    )
    html = f"<pre>{plain}</pre>"
    _send(to_email, subject, html, plain)


def send_campaign_complete(
    to_email: str,
    campaign_name: str,
    campaign_id: int,
    targets_count: int,
    emails_sent: int,
    opened_count: int,
    clicked_count: int,
    submitted_count: int,
) -> None:
    open_rate = round(opened_count / emails_sent * 100) if emails_sent else 0
    click_rate = round(clicked_count / emails_sent * 100) if emails_sent else 0
    submit_rate = round(submitted_count / emails_sent * 100) if emails_sent else 0

    if click_rate >= 30:
        risk_label, risk_color = "Risque élevé", "#ef4444"
    elif click_rate >= 15:
        risk_label, risk_color = "Risque modéré", "#f59e0b"
    elif click_rate > 0:
        risk_label, risk_color = "Risque faible", "#22c55e"
    else:
        risk_label, risk_color = "Aucun clic", "#22c55e"

    detail_url = f"{settings.FRONTEND_URL}/cyberscan/phishing/campaigns/{campaign_id}"

    plain = f"""Bonjour,

Votre campagne de simulation de phishing "{campaign_name}" est terminée.

━━━ Résultats ━━━
  Cibles         : {targets_count}
  Emails envoyés : {emails_sent}
  Taux d'ouverture : {open_rate}% ({opened_count} / {emails_sent})
  Taux de clic   : {click_rate}% ({clicked_count} / {emails_sent})
  Identifiants saisis : {submit_rate}% ({submitted_count} / {emails_sent})
  Niveau de risque : {risk_label}

Voir les résultats détaillés et télécharger le rapport PDF :
{detail_url}

---
Rocher Cybersécurité — Simulation de phishing
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
  <tr><td style="background:linear-gradient(135deg,#1e1b4b,#0f172a);padding:32px 40px;border-bottom:2px solid #4f46e5;text-align:center;border-radius:12px 12px 0 0;">
    <p style="margin:0 0 6px;color:#a5b4fc;font-size:12px;font-weight:800;letter-spacing:2px;">SIMULATION TERMINÉE ✓</p>
    <h1 style="margin:0;color:#f8fafc;font-size:22px;line-height:1.3;">{campaign_name}</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:10px;margin-bottom:24px;">
      <tr>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Cibles</p>
          <p style="margin:6px 0 0;color:#f8fafc;font-size:26px;font-weight:800;">{targets_count}</p>
        </td>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Ouvertures</p>
          <p style="margin:6px 0 0;color:#f8fafc;font-size:26px;font-weight:800;">{open_rate}<span style="font-size:14px;color:#94a3b8;">%</span></p>
        </td>
        <td style="padding:16px;text-align:center;border-right:1px solid #1e293b;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Clics</p>
          <p style="margin:6px 0 0;font-size:26px;font-weight:800;color:{risk_color};">{click_rate}<span style="font-size:14px;color:#94a3b8;">%</span></p>
        </td>
        <td style="padding:16px;text-align:center;">
          <p style="margin:0;color:#64748b;font-size:10px;text-transform:uppercase;letter-spacing:1px;">Identifiants</p>
          <p style="margin:6px 0 0;font-size:26px;font-weight:800;color:{'#ef4444' if submitted_count > 0 else '#22c55e'};">{submit_rate}<span style="font-size:14px;color:#94a3b8;">%</span></p>
        </td>
      </tr>
    </table>
    <div style="background:{risk_color}18;border:1px solid {risk_color}44;border-radius:8px;padding:14px 20px;margin-bottom:28px;display:flex;align-items:center;">
      <p style="margin:0;color:#e2e8f0;font-size:14px;">Niveau de risque : <strong style="color:{risk_color};">{risk_label}</strong> — basé sur {click_rate}% de taux de clic</p>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
      <a href="{detail_url}" style="display:inline-block;background:#4f46e5;color:#fff;text-decoration:none;padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">Voir les résultats détaillés →</a>
    </td></tr></table>
    <p style="color:#475569;font-size:12px;text-align:center;margin:20px 0 0;">Le rapport PDF est disponible depuis la page de résultats.</p>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
    <p style="margin:0;color:#475569;font-size:12px;">Rocher Cybersécurité — Simulation de phishing</p>
  </td></tr>
</table></td></tr></table></body></html>"""

    subject = f"[Rocher Cybersécurité] Campagne terminée — {campaign_name} ({click_rate}% de clic)"
    _send(to_email, subject, html, plain)


def send_contact_email(
    name: str,
    email: str,
    phone: str | None,
    need_type: str,
    site_url: str | None,
    message: str,
    contact_email: str,
) -> None:
    need_labels = {
        "audit-flash": "Audit Flash (290 € HT)",
        "audit-app": "Audit App-Check (725 € HT)",
        "pentest": "Pentest léger (1 900 € HT)",
        "simulation-phishing": "Simulation de phishing",
        "abonnement": "Abonnement surveillance continue",
        "autre": "Autre / Demande de devis",
    }
    need_label = need_labels.get(need_type, need_type)

    subject = f"[Rocher Cybersécurité Contact] {need_label} — {name} <{email}>"

    plain_owner = f"""Nouvelle demande de contact via Rocher Cybersécurité

Nom     : {name}
Email   : {email}
Tél.    : {phone or '—'}
Besoin  : {need_label}
Site    : {site_url or '—'}

Message :
{message}

---
Répondre à : {email}
"""
    html_owner = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#0e7490,#0369a1);padding:28px 40px;border-radius:12px 12px 0 0;">
<h1 style="margin:0;color:#fff;font-size:20px;">Nouvelle demande de contact</h1>
<p style="margin:6px 0 0;color:#bae6fd;font-size:13px;">{need_label}</p>
</td></tr>
<tr><td style="padding:32px 40px;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;padding:20px;margin-bottom:24px;">
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">NOM</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{name}</p>
</td></tr>
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">EMAIL</p>
  <p style="margin:4px 0 0;color:#22d3ee;font-size:15px;"><a href="mailto:{email}" style="color:#22d3ee;">{email}</a></p>
</td></tr>
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">TÉLÉPHONE</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{phone or '—'}</p>
</td></tr>
<tr><td style="padding:8px 0;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">SITE / URL</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{site_url or '—'}</p>
</td></tr>
</table>
<p style="color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;margin:0 0 8px;">MESSAGE</p>
<div style="background:#0f172a;border-radius:8px;padding:16px;color:#cbd5e1;font-size:14px;line-height:1.7;white-space:pre-wrap;">{message}</div>
<table width="100%" cellpadding="0" cellspacing="0" style="margin-top:28px;"><tr><td>
<a href="mailto:{email}" style="display:inline-block;background:#0e7490;color:#fff;text-decoration:none;
padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;">Répondre à {name} →</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
<p style="margin:0;color:#475569;font-size:12px;">Rocher Cybersécurité — Formulaire de contact</p>
</td></tr>
</table></td></tr></table></body></html>"""

    _send(contact_email, subject, html_owner, plain_owner)

    # Confirmation to sender
    plain_confirm = f"""Bonjour {name},

Votre message a bien été reçu. Je reviendrai vers vous sous 4 h (jours ouvrés 9h–18h).

Récapitulatif de votre demande :
  Type : {need_label}
  Site : {site_url or '—'}

---
Rocher Cybersécurité
contact@cyberscanapp.com
"""
    html_confirm = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#0e7490,#0369a1);padding:28px 40px;border-radius:12px 12px 0 0;text-align:center;">
<h1 style="margin:0;color:#fff;font-size:22px;">Message bien reçu ✓</h1>
</td></tr>
<tr><td style="padding:32px 40px;">
<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">
Bonjour <strong style="color:#f8fafc;">{name}</strong>,
</p>
<p style="color:#94a3b8;font-size:15px;line-height:1.7;margin:0 0 20px;">
Votre demande concernant <strong style="color:#22d3ee;">{need_label}</strong> a bien été reçue.
Je vous répondrai sous <strong style="color:#f8fafc;">4 heures</strong> (jours ouvrés, 9h–18h).
</p>
<p style="color:#475569;font-size:13px;line-height:1.7;margin:0;">
Rocher Cybersécurité<br>
<a href="mailto:contact@cyberscanapp.com" style="color:#22d3ee;">contact@cyberscanapp.com</a>
</p>
</td></tr>
</table></td></tr></table></body></html>"""

    try:
        _send(
            email,
            "[Rocher Cybersécurité] Votre message a bien été reçu",
            html_confirm,
            plain_confirm,
        )
    except Exception as e:
        logger.warning(f"Envoi email confirmation contact échoué: {e}")


def send_booking_confirmation(
    to_email: str,
    name: str,
    date_label: str,
    time_label: str,
    duration_minutes: int,
    slot_label: str,
    need_type: str,
    cancel_url: str,
) -> None:
    need_labels = {
        "audit-flash": "Audit Flash",
        "audit-app": "Audit App-Check",
        "pentest": "Pentest léger",
        "abonnement": "Abonnement surveillance",
        "autre": "Autre / Devis",
    }
    need_label = need_labels.get(need_type, need_type)
    subject = f"[Rocher Cybersécurité] Réservation confirmée — {date_label} à {time_label}"
    plain = f"""Bonjour {name},

Votre rendez-vous est confirmé :

  Date     : {date_label}
  Heure    : {time_label} ({duration_minutes} min)
  Objet    : {slot_label}
  Prestation : {need_label}

Pour annuler votre réservation :
{cancel_url}

À bientôt,
David Rocher — Rocher Cybersécurité
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0f172a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#1e293b;border-radius:12px;border:1px solid #334155;">
<tr><td style="background:linear-gradient(135deg,#065f46,#0369a1);padding:28px 40px;border-radius:12px 12px 0 0;text-align:center;">
<p style="margin:0 0 4px;color:#6ee7b7;font-size:12px;font-weight:700;letter-spacing:2px;">RÉSERVATION CONFIRMÉE ✓</p>
<h1 style="margin:0;color:#fff;font-size:22px;">{slot_label}</h1>
</td></tr>
<tr><td style="padding:32px 40px;">
<p style="color:#94a3b8;font-size:15px;margin:0 0 24px;">Bonjour <strong style="color:#f8fafc;">{name}</strong>,</p>
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0f172a;border-radius:8px;padding:20px;margin-bottom:24px;">
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">DATE</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:16px;font-weight:700;">{date_label}</p>
</td></tr>
<tr><td style="padding:8px 0;border-bottom:1px solid #1e293b;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">HEURE</p>
  <p style="margin:4px 0 0;color:#22d3ee;font-size:16px;font-weight:700;">{time_label} ({duration_minutes} min)</p>
</td></tr>
<tr><td style="padding:8px 0;">
  <p style="margin:0;color:#64748b;font-size:11px;font-weight:700;letter-spacing:1px;">PRESTATION</p>
  <p style="margin:4px 0 0;color:#f8fafc;font-size:15px;">{need_label}</p>
</td></tr>
</table>
<p style="color:#64748b;font-size:13px;line-height:1.7;margin:0 0 24px;">
Pour annuler votre réservation, cliquez ci-dessous (jusqu'à 24h avant le rendez-vous).
</p>
<table width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">
<a href="{cancel_url}" style="display:inline-block;background:#475569;color:#fff;text-decoration:none;
padding:11px 24px;border-radius:8px;font-size:13px;">Annuler ma réservation</a>
</td></tr></table>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid #334155;text-align:center;">
<p style="margin:0;color:#475569;font-size:12px;">David Rocher — Rocher Cybersécurité · Trévoux (01)</p>
</td></tr>
</table></td></tr></table></body></html>"""
    _send(to_email, subject, html, plain)


def send_booking_admin_notification(
    admin_email: str,
    name: str,
    email: str,
    phone: str | None,
    date_label: str,
    time_label: str,
    need_type: str,
    message: str | None,
) -> None:
    need_labels = {
        "audit-flash": "Audit Flash (290 €)",
        "audit-app": "Audit App-Check (725 €)",
        "pentest": "Pentest léger (1 900 €)",
        "simulation-phishing": "Simulation de phishing",
        "abonnement": "Abonnement surveillance",
        "autre": "Autre / Devis",
    }
    need_label = need_labels.get(need_type, need_type)
    subject = f"[Rocher Cybersécurité] Nouvelle réservation — {name} le {date_label} à {time_label}"
    plain = f"""Nouvelle réservation

  Nom      : {name}
  Email    : {email}
  Tél.     : {phone or '—'}
  Date     : {date_label} à {time_label}
  Prestation : {need_label}
  Message  : {message or '—'}

Répondre à : {email}
"""
    html = f"""<p>Nouvelle réservation de <strong>{name}</strong> ({email})<br>
Le <strong>{date_label} à {time_label}</strong> — {need_label}</p>
<p>Message : {message or '—'}</p>
<p><a href="mailto:{email}">Répondre</a></p>"""
    _send(admin_email, subject, html, plain)
