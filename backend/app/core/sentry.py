"""Scrubbing PII des évènements Sentry (défense en profondeur — audit #16).

`send_default_pii` est laissé à False (défaut) et confirmé explicitement à l'init,
mais une régression future pourrait interpoler une adresse e-mail, un token JWT ou
une clé dans le message d'une exception. Le hook `before_send` masque ces motifs
AVANT l'envoi au SaaS Sentry : e-mails masqués (j***@corp.com) et secrets remplacés
par [REDACTED]. On ne dépend d'aucune structure d'évènement particulière : on parcourt
récursivement les chaînes de l'évènement.
"""

from __future__ import annotations

import re
from typing import Any

# Adresse e-mail : masquée en conservant la 1re lettre + le domaine (cf. mask_email).
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
# JWT (trois segments base64url séparés par des points) — token de session/refresh.
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+")
# Affectation d'un secret (password/token/secret/api_key/authorization = <valeur>).
_SECRET_ASSIGN_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|token|secret|api[_-]?key|authorization|bearer)"
    r"([\"']?\s*[:=]\s*[\"']?)([^\s\"',;]+)"
)


def _mask_email_match(m: re.Match[str]) -> str:
    email = m.group(0)
    local, _, domain = email.partition("@")
    return f"{local[0] if local else ''}***@{domain}"


def _scrub_text(text: str) -> str:
    """Masque e-mails, JWT et affectations de secret dans une chaîne."""
    text = _JWT_RE.sub("[REDACTED]", text)
    text = _SECRET_ASSIGN_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED]", text)
    text = _EMAIL_RE.sub(_mask_email_match, text)
    return text


def _scrub(value: Any) -> Any:
    """Parcourt récursivement dicts/listes/chaînes et scrubbe les chaînes."""
    if isinstance(value, str):
        return _scrub_text(value)
    if isinstance(value, dict):
        return {k: _scrub(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return type(value)(_scrub(v) for v in value)
    return value


def scrub_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """Hook `before_send` Sentry : renvoie l'évènement avec ses PII masquées."""
    return _scrub(event)


def init_sentry(dsn: str, environment: str) -> None:
    """Initialise Sentry avec scrubbing PII et send_default_pii explicitement à False."""
    import sentry_sdk

    sentry_sdk.init(
        dsn=dsn,
        traces_sample_rate=0.1,
        environment=environment,
        send_default_pii=False,
        before_send=scrub_event,
    )
