"""
Email service package.

Re-exporte toutes les fonctions publiques pour maintenir la compatibilité avec
les imports existants de la forme :

    from app.services.email_service import send_password_reset
    from app.services.email_service import _send
    ...

Sous-modules :
  base      — _send, _send_via_resend, _send_via_smtp
  auth      — send_password_reset
  scan      — send_scan_report, send_ssl_expiry_alert, send_monthly_digest
  alerts    — send_url_scan_alert, send_campaign_complete,
              send_contact_email, send_booking_confirmation,
              send_booking_admin_notification
  awareness — send_awareness_magic_link, send_awareness_completion,
              send_awareness_at_risk_alert
"""

from .alerts import (
    send_booking_admin_notification,
    send_booking_confirmation,
    send_campaign_complete,
    send_contact_email,
    send_url_scan_alert,
)
from .auth import send_password_reset
from .awareness import (
    send_awareness_at_risk_alert,
    send_awareness_completion,
    send_awareness_magic_link,
)
from .base import _send, _send_via_resend, _send_via_smtp
from .scan import send_monthly_digest, send_scan_report, send_ssl_expiry_alert

__all__ = [
    # base
    "_send",
    "_send_via_resend",
    "_send_via_smtp",
    # auth
    "send_password_reset",
    # scan
    "send_scan_report",
    "send_ssl_expiry_alert",
    "send_monthly_digest",
    # alerts
    "send_url_scan_alert",
    "send_campaign_complete",
    "send_contact_email",
    "send_booking_confirmation",
    "send_booking_admin_notification",
    # awareness
    "send_awareness_magic_link",
    "send_awareness_completion",
    "send_awareness_at_risk_alert",
]
