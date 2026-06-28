"""Emails liés à l'authentification : reset de mot de passe."""

from .base import _send


def send_password_reset(to_email: str, reset_url: str) -> None:
    plain = f"""Bonjour,

Vous avez demandé la réinitialisation de votre mot de passe CyberScan.

Cliquez sur le lien ci-dessous pour choisir un nouveau mot de passe (valable 30 minutes) :

{reset_url}

Si vous n'avez pas fait cette demande, ignorez cet email — votre mot de passe reste inchangé.

---
CyberScan — Cybersécurité as a Service
"""
    html = f'<p>Bonjour,</p><p>Cliquez ici pour réinitialiser votre mot de passe (valable 30 minutes) :</p><p><a href="{reset_url}">{reset_url}</a></p>'
    _send(to_email, "[CyberScan] Réinitialisation de votre mot de passe", html, plain)
