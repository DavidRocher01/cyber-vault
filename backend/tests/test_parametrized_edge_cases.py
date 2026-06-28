"""
I2 — Tests paramétrés sur les edge cases critiques.
Couvre les inputs limites que les happy-path tests ignorent.
"""

import pytest
from pydantic import ValidationError

from app.schemas.vault_item import VaultItemCreate, VaultItemUpdate

# ── Vault : validation de catégorie ──────────────────────────────────────────


@pytest.mark.parametrize(
    "category,expected",
    [
        ("login", "login"),
        ("card", "card"),
        ("note", "note"),
        ("wifi", "wifi"),
        ("other", "other"),
        ("invalid_cat", "login"),  # fallback
        ("", "login"),  # empty string
        ("LOGIN", "login"),  # case sensitive — invalid → fallback
        ("a" * 32, "login"),  # max_length — invalid category → fallback
        ("<script>alert(1)</script>", "login"),  # XSS attempt
        (None, "login"),  # None — defaults
    ],
)
def test_vault_category_validation(category, expected):
    item = VaultItemCreate(
        title_encrypted="x",
        password_encrypted="enc",
        category=category if category is not None else "login",
    )
    assert item.category == expected


@pytest.mark.parametrize(
    "category,expected",
    [
        ("card", "card"),
        ("INVALID", "login"),
        ("", "login"),
        (None, None),  # None means "don't change"
    ],
)
def test_vault_update_category_validation(category, expected):
    item = VaultItemUpdate(category=category)
    assert item.category == expected


# ── Vault : zero-knowledge strict (aucun champ en clair accepté) ─────────────


def test_vault_create_accepts_encrypted_only():
    item = VaultItemCreate(password_encrypted="enc", title_encrypted="blob")
    assert item.title_encrypted == "blob"
    assert item.password_encrypted == "enc"


@pytest.mark.parametrize("field", ["title", "username", "url", "notes"])
def test_vault_create_rejects_plaintext_field(field):
    # extra='forbid' : tout champ en clair est rejeté (P1-4).
    with pytest.raises(ValidationError):
        VaultItemCreate(**{field: "leak", "password_encrypted": "enc"})


def test_vault_create_requires_nonempty_password_encrypted():
    with pytest.raises(ValidationError):
        VaultItemCreate(password_encrypted="", title_encrypted="blob")


@pytest.mark.parametrize(
    "title_encrypted,should_pass",
    [
        ("A" * 16384, True),  # exactly at limit
        ("A" * 16385, False),  # above limit
    ],
)
def test_vault_title_encrypted_length(title_encrypted, should_pass):
    if should_pass:
        item = VaultItemCreate(password_encrypted="enc", title_encrypted=title_encrypted)
        assert item.title_encrypted == title_encrypted
    else:
        with pytest.raises(ValidationError):
            VaultItemCreate(password_encrypted="enc", title_encrypted=title_encrypted)
