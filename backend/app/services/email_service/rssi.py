"""E-mails du module RSSI externalise (espace client)."""

from .base import _send


def send_portal_invitation(
    to_email: str,
    invite_url: str,
    client_name: str | None = None,
    consultant_name: str | None = None,
    token_ttl_days: int = 7,
) -> None:
    """Invitation d'un client a son espace RSSI : e-mail de bienvenue dediE (et non
    le mail generique de reinitialisation de mot de passe). Le lien mene a la page
    d'activation ou le client definit son mot de passe (valable token_ttl_days jours)."""
    org = f" pour {client_name}" if client_name else ""
    by = (
        f"Votre consultant {consultant_name} vous"
        if consultant_name
        else "Votre consultant RSSI vous"
    )
    subject = "[Rocher Cybersécurité] Votre espace client RSSI est prêt"
    plain = f"""Bonjour,

{by} a ouvert un espace client dédié{org} sur la plateforme Rocher Cybersécurité.

Vous y suivrez en temps réel votre accompagnement RSSI : visites planifiées, plan
d'actions, livrables et sites surveillés.

Pour activer votre accès, définissez votre mot de passe via le lien ci-dessous
(valable {token_ttl_days} jours) :

{invite_url}

Une fois votre mot de passe défini, connectez-vous pour accéder à votre espace.
Si vous ne vous attendiez pas à cette invitation, ignorez simplement cet e-mail.

---
Rocher Cybersécurité — RSSI externalisé
"""
    html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#030712;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#030712;">
<tr><td align="center" style="padding:40px 20px;">
<table width="600" cellpadding="0" cellspacing="0" style="background:#111827;border-radius:12px;border:1px solid #1f2937;">
  <tr><td style="background:linear-gradient(135deg,#0e7490,#1d4ed8);padding:32px 40px;border-radius:12px 12px 0 0;text-align:center;">
    <p style="margin:0 0 6px;color:#a5f3fc;font-size:12px;font-weight:800;letter-spacing:2px;">RSSI EXTERNALISÉ</p>
    <h1 style="margin:0;color:#fff;font-size:22px;">Votre espace client est prêt</h1>
  </td></tr>
  <tr><td style="padding:32px 40px;">
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 8px;">Bonjour,</p>
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 20px;">
      {by} a ouvert un espace client dédié{org} sur la plateforme
      <strong style="color:#f9fafb;">Rocher Cybersécurité</strong>. Vous y suivrez en temps réel
      votre accompagnement : visites planifiées, plan d'actions, livrables et sites surveillés.
    </p>
    <p style="color:#9ca3af;font-size:15px;line-height:1.7;margin:0 0 24px;">
      Pour activer votre accès, définissez votre mot de passe :
    </p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
      <tr><td align="center">
        <a href="{invite_url}" style="display:inline-block;background:#0891b2;color:#fff;text-decoration:none;
        padding:14px 36px;border-radius:8px;font-weight:700;font-size:15px;">
          Activer mon espace
        </a>
      </td></tr>
    </table>
    <div style="background:#1f2937;border-radius:8px;padding:14px 18px;margin-bottom:20px;">
      <p style="margin:0;color:#6b7280;font-size:12px;word-break:break-all;">{invite_url}</p>
    </div>
    <p style="color:#6b7280;font-size:12px;line-height:1.6;margin:0;">
      Ce lien est personnel et expire dans <strong style="color:#9ca3af;">{token_ttl_days} jours</strong>.<br>
      Si vous ne vous attendiez pas à cette invitation, ignorez cet e-mail.
    </p>
  </td></tr>
  <tr><td style="padding:20px 40px;border-top:1px solid #1f2937;text-align:center;">
    <p style="margin:0;color:#4b5563;font-size:12px;">Rocher Cybersécurité — RSSI externalisé</p>
  </td></tr>
</table></td></tr></table></body></html>"""
    _send(to_email, subject, html, plain)
