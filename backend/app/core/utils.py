import json
from typing import Any


def mask_email(email: str | None) -> str:
    """Masque une adresse email pour les logs (anti-PII) : j***@corp.com.
    Conserve le 1er caractère local + le domaine (utile au debug, PII réduite)."""
    if not email or "@" not in email:
        return "<email>"
    local, _, domain = email.partition("@")
    prefix = local[0] if local else ""
    return f"{prefix}***@{domain}"


def safe_json_load(value: str | None, default: Any = None) -> Any:
    """Parse a JSON string, returning `default` on any error or empty input."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default
