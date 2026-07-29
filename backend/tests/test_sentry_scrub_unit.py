"""Tests unitaires du scrubbing PII Sentry `before_send` (audit #16).

Le hook `scrub_event` doit masquer e-mails, JWT et affectations de secret
partout dans l'évènement (chaînes imbriquées dans dicts/listes/tuples).
Tests purs — aucune init réseau Sentry.
"""

from app.core.sentry import _scrub, _scrub_text, scrub_event


def test_scrub_masks_email_keeping_first_letter_and_domain():
    assert _scrub_text("contact jean.dupont@corp.com now") == "contact j***@corp.com now"


def test_scrub_redacts_jwt():
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjMifQ.abc123_-XY"
    assert _scrub_text(f"token={jwt}") == "token=[REDACTED]"


def test_scrub_redacts_secret_assignments():
    assert _scrub_text('password="hunter2"') == 'password="[REDACTED]"'
    assert _scrub_text("api_key: sk-live-abcdef") == "api_key: [REDACTED]"
    assert _scrub_text("secret=s3cr3tValue") == "secret=[REDACTED]"
    # La valeur immédiatement après l'affectation est masquée (ici le schéma « Bearer »).
    assert _scrub_text("authorization=Bearer") == "authorization=[REDACTED]"


def test_scrub_leaves_benign_text_untouched():
    assert _scrub_text("scan terminé sans anomalie") == "scan terminé sans anomalie"


def test_scrub_recurses_into_nested_structures():
    event = {
        "message": "login failed for alice@example.org",
        "extra": {
            "creds": ["password=topsecret", {"token": "eyJa.bBb.cCc"}],
        },
        "tuple_field": ("bob@x.io",),
    }
    scrubbed = _scrub(event)

    assert scrubbed["message"] == "login failed for a***@example.org"
    assert scrubbed["extra"]["creds"][0] == "password=[REDACTED]"
    assert scrubbed["extra"]["creds"][1]["token"] == "[REDACTED]"
    assert scrubbed["tuple_field"] == ("b***@x.io",)


def test_scrub_event_returns_scrubbed_event():
    event = {"message": "erreur pour user@site.fr"}
    result = scrub_event(event, {})
    assert result["message"] == "erreur pour u***@site.fr"


def test_scrub_preserves_non_string_values():
    event = {"level": "error", "count": 3, "flag": True, "nothing": None}
    assert _scrub(event) == event
