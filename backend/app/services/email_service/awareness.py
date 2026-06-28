"""Emails liés au module Sensibilisation NIS2 : magic-link, completion, alertes."""

from .base import _send


def send_awareness_magic_link(
    to_email: str,
    first_name: str | None,
    org_name: str,
    login_url: str,
    token_ttl_minutes: int = 30,
) -> None:
    greeting = f"Bonjour{' ' + first_name if first_name else ''},"
    subject = f"[Rocher Cybersécurité] Votre lien de connexion — {org_name}"
    plain = f"""{greeting}

Vous avez été invité(e) à rejoindre la plateforme de sensibilisation NIS2 de {org_name}.

Cliquez sur le lien ci-dessous pour accéder à votre espace de formation (valable {token_ttl_minutes} minutes) :

{login_url}

Ce lien est personnel et à usage unique. Si vous n'avez pas demandé cet accès, ignorez cet email.

---
Rocher Cybersécurité — Sensibilisation NIS2
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#030712;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030712;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:12px;border:1px solid #1f2937;">
  <tr><td style="background:linear-gradient(135deg,#0e7490,#1d4ed8);padding:32px 40px;border-radius:12px 12px 0 0;text-align:center;">
    <p style="margin:0 0 6px;color:#a5f3fc;font-size:12px;font-weight:800;letter-spacing:2px;">SENSIBILISATION NIS2</p>
    <h1 style="margin:0;color:#fff;font-size:22px;">Votre lien de connexion</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 8px;">{greeting}</p>
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 24px;">
      Vous avez été invité(e) à rejoindre la plateforme de formation cybersécurité de
      <strong style="color:#f9fafb;">{org_name}</strong>.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr><td align="center">
        <a href="{login_url}" style="display:inline-block;background:#0891b2;color:#fff;text-decoration:none;
        padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">
          Accéder à ma formation
        </a>
      </td></tr>
    </table>
    <div style="background:#1f2937;border-radius:8px;padding:14px 18px;margin-bottom:20px;">
      <p style="margin:0;color:#6b7280;font-size:12px;word-break:break-all;">{login_url}</p>
    </div>
    <p style="color:#6b7280;font-size:12px;line-height:1.6;margin:0;">
      Ce lien est personnel, à usage unique et expire dans <strong style="color:#9ca3af;">{token_ttl_minutes} minutes</strong>.<br>
      Si vous n'avez pas demandé cet accès, ignorez cet email.
    </p>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #1f2937;text-align:center;">
    <p style="margin:0;color:#4b5563;font-size:12px;">Rocher Cybersécurité — Sensibilisation NIS2</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    _send(to_email, subject, html, plain)


def send_awareness_completion(
    to_email: str,
    first_name: str | None,
    program_title: str,
    org_name: str,
    certificate_url: str,
) -> None:
    greeting = f"Bonjour{' ' + first_name if first_name else ''},"
    subject = "[Rocher Cybersécurité] Félicitations — Attestation NIS2 obtenue !"
    plain = f"""{greeting}

Bravo ! Vous avez complété le programme de sensibilisation NIS2 de {org_name}.

Programme : {program_title}
Attestation vérifiable disponible ici : {certificate_url}

Cette attestation prouve votre formation cybersécurité conforme NIS2 Article 21.

---
Rocher Cybersécurité — Sensibilisation NIS2
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#030712;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030712;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:12px;border:1px solid #1f2937;">
  <tr><td style="background:linear-gradient(135deg,#065f46,#0d9488);padding:32px 40px;border-radius:12px 12px 0 0;text-align:center;">
    <p style="margin:0 0 6px;color:#6ee7b7;font-size:12px;font-weight:800;letter-spacing:2px;">PROGRAMME COMPLÉTÉ ✓</p>
    <h1 style="margin:0;color:#fff;font-size:22px;">Félicitations !</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 8px;">{greeting}</p>
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 24px;">
      Vous avez complété le programme <strong style="color:#f9fafb;">{program_title}</strong>
      de <strong style="color:#f9fafb;">{org_name}</strong>.
      Votre attestation NIS2 vérifiable est disponible.
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr><td align="center">
        <a href="{certificate_url}" style="display:inline-block;background:#0d9488;color:#fff;text-decoration:none;
        padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">
          Télécharger mon attestation
        </a>
      </td></tr>
    </table>
    <p style="color:#6b7280;font-size:12px;line-height:1.6;margin:0;">
      Cette attestation est vérifiable publiquement et certifie votre formation conformément à l'Article 21 de la directive NIS2.
    </p>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #1f2937;text-align:center;">
    <p style="margin:0;color:#4b5563;font-size:12px;">Rocher Cybersécurité — Sensibilisation NIS2</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    _send(to_email, subject, html, plain)


def send_awareness_at_risk_alert(
    to_email: str,
    org_name: str,
    at_risk_count: int,
    dashboard_url: str,
) -> None:
    subject = f"[Rocher Cybersécurité] {at_risk_count} learner(s) à risque — {org_name}"
    plain = f"""Bonjour,

Un rapport hebdomadaire de sensibilisation NIS2 est disponible pour {org_name}.

{at_risk_count} learner(s) n'ont pas progressé depuis plus de 14 jours et risquent de ne pas obtenir leur attestation avant l'échéance.

Consultez le tableau de bord pour les identifier et leur renvoyer un lien de connexion :
{dashboard_url}

---
Rocher Cybersécurité — Sensibilisation NIS2
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#030712;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030712;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:12px;border:1px solid #1f2937;">
  <tr><td style="background:linear-gradient(135deg,#7c1c1c,#991b1b);padding:32px 40px;border-radius:12px 12px 0 0;text-align:center;">
    <p style="margin:0 0 6px;color:#fca5a5;font-size:12px;font-weight:800;letter-spacing:2px;">ALERTE FORMATION</p>
    <h1 style="margin:0;color:#fff;font-size:22px;">{at_risk_count} learner(s) à risque</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 20px;">
      <strong style="color:#f9fafb;">{at_risk_count} learner(s)</strong> de
      <strong style="color:#f9fafb;">{org_name}</strong> n'ont pas progressé depuis plus de 14 jours
      et ont un taux de complétion inférieur à 70 %.
    </p>
    <div style="background:#1f2937;border-radius:8px;padding:16px 20px;margin-bottom:24px;">
      <p style="margin:0;color:#9ca3af;font-size:13px;">
        Pensez à leur renvoyer un lien de connexion depuis le tableau de bord pour les relancer.
      </p>
    </div>
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr><td align="center">
        <a href="{dashboard_url}" style="display:inline-block;background:#dc2626;color:#fff;text-decoration:none;
        padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">
          Voir les learners à risque
        </a>
      </td></tr>
    </table>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #1f2937;text-align:center;">
    <p style="margin:0;color:#4b5563;font-size:12px;">Rocher Cybersécurité — Sensibilisation NIS2</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    _send(to_email, subject, html, plain)
