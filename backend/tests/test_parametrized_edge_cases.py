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
        ("a" * 100, "login"),  # trop long — invalid → fallback
        ("<script>alert(1)</script>", "login"),  # XSS attempt
        (None, "login"),  # None — defaults
    ],
)
def test_vault_category_validation(category, expected):
    item = VaultItemCreate(
        title="Test",
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


# ── Vault : validation des champs texte ──────────────────────────────────────


@pytest.mark.parametrize(
    "title",
    [
        "A",  # minimum (1 char)
        "A" * 200,  # maximum (200 chars)
        "Titre avec espaces",
        "Titre-avec-tirets",
        "Title 123!@#",
    ],
)
def test_vault_title_valid(title):
    item = VaultItemCreate(title=title, password_encrypted="enc")
    assert item.title == title


@pytest.mark.parametrize(
    "title",
    [
        "",  # empty — below min_length=1
        "A" * 201,  # above max_length=200
    ],
)
def test_vault_title_invalid(title):
    with pytest.raises(ValidationError):  # pydantic ValidationError
        VaultItemCreate(title=title, password_encrypted="enc")


# ── Vault : URL field ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "url,should_pass",
    [
        ("https://example.com", True),
        ("http://localhost", True),
        (None, True),
        ("A" * 2048, True),  # exactly at limit
        ("A" * 2049, False),  # above limit
    ],
)
def test_vault_url_length(url, should_pass):
    if should_pass:
        item = VaultItemCreate(title="T", password_encrypted="enc", url=url)
        assert item.url == url
    else:
        with pytest.raises(ValidationError):
            VaultItemCreate(title="T", password_encrypted="enc", url=url)


# ── Vault : notes field ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "notes,should_pass",
    [
        (None, True),
        ("", True),
        ("A" * 10000, True),  # exactly at limit
        ("A" * 10001, False),  # above limit
    ],
)
def test_vault_notes_length(notes, should_pass):
    if should_pass:
        item = VaultItemCreate(title="T", password_encrypted="enc", notes=notes)
        assert item.notes == notes
    else:
        with pytest.raises(ValidationError):
            VaultItemCreate(title="T", password_encrypted="enc", notes=notes)
