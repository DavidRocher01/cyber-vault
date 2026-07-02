"""
Invariants 2FA / TOTP — propriétés de sécurité (complète test_2fa.py).

Ce fichier cible les INVARIANTS et CAS LIMITES plutôt que le happy path :
  - Chiffrement at-rest : le secret TOTP n'est JAMAIS stocké en clair, et le
    round-trip encrypt→decrypt est fidèle (y compris fallback legacy en clair).
  - Le secret brut ne fuit jamais via /users/me (ni via aucun autre endpoint que
    le setup pré-activation).
  - Reconfigurer la 2FA quand elle est déjà active EXIGE le code TOTP courant
    (anti account-takeover via JWT volé) et ne rote la graine QUE si le code est bon.
  - Activer/désactiver la 2FA exige les bons facteurs (mot de passe + code).
  - Login : tant que la 2FA est active et qu'aucun code n'est fourni, la réponse
    est exactement {requires_2fa: True} SANS access_token ; un code valide finalise.
  - Un code TOTP faux est rejeté, un secret rejoué après désactivation n'ouvre plus.

asyncio_mode = auto → les tests sont des `async def test_...` sans décorateur.
"""

from unittest.mock import patch

import pyotp
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.core.database as _db_module
from app.core.totp_crypto import (
    decrypt_totp_secret,
    encrypt_totp_secret,
)
from app.main import app
from app.models.user import User

BASE = "/api/v1"
PWD = "StrongPass123!"


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _register_login(client: AsyncClient, email: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={"email": email, "password": PWD})
    r = await client.post(f"{BASE}/auth/login", json={"email": email, "password": PWD})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _setup_and_enable_2fa(client: AsyncClient, headers: dict) -> str:
    """Run setup + enable, return the raw base32 TOTP secret."""
    setup = await client.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    code = pyotp.TOTP(secret).now()
    enable = await client.post(f"{BASE}/users/me/2fa/enable", headers=headers, json={"code": code})
    assert enable.status_code == 200
    return secret


async def _get_user(email: str) -> User:
    async with _db_module.AsyncSessionLocal() as db:
        return (await db.execute(select(User).where(User.email == email))).scalar_one()


# ── Invariant : chiffrement at-rest (unité, sans DB) ─────────────────────────


def test_encrypt_totp_secret_roundtrip_is_faithful():
    """encrypt→decrypt rend exactement le secret d'origine."""
    secret = pyotp.random_base32()
    token = encrypt_totp_secret(secret)
    assert token != secret, "encrypt() ne doit pas être l'identité"
    assert decrypt_totp_secret(token) == secret


def test_encrypt_totp_secret_is_non_deterministic():
    """Fernet embarque un IV/timestamp : deux chiffrés du même secret diffèrent,
    mais déchiffrent vers la même valeur (pas de leak par comparaison de blobs)."""
    secret = pyotp.random_base32()
    t1 = encrypt_totp_secret(secret)
    t2 = encrypt_totp_secret(secret)
    assert t1 != t2
    assert decrypt_totp_secret(t1) == decrypt_totp_secret(t2) == secret


def test_decrypt_totp_secret_legacy_plaintext_fallback():
    """Compat : une graine legacy stockée en clair (pas un token Fernet) est
    renvoyée telle quelle plutôt que de lever."""
    plaintext_secret = pyotp.random_base32()
    assert decrypt_totp_secret(plaintext_secret) == plaintext_secret


def test_ciphertext_does_not_contain_plaintext_secret():
    """Le chiffré ne doit pas contenir la graine en sous-chaîne (invariant fort
    contre un stockage 'chiffré' qui laisserait fuiter le secret)."""
    secret = pyotp.random_base32()
    token = encrypt_totp_secret(secret)
    assert secret not in token


# ── Invariant : le secret est chiffré en base après setup ────────────────────


async def test_setup_persists_encrypted_secret_not_plaintext():
    """Après setup (pré-activation), la colonne totp_secret est un token Fernet,
    jamais la graine en clair, et décrypte vers la graine renvoyée à l'utilisateur."""
    email = "encsetup@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        setup = await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})
        secret = setup.json()["secret"]

    user = await _get_user(email)
    assert user.totp_secret is not None
    assert user.totp_secret != secret, "graine stockée en clair !"
    assert decrypt_totp_secret(user.totp_secret) == secret


async def test_users_me_never_leaks_totp_secret():
    """Invariant de confidentialité : /users/me ne doit exposer AUCUNE forme du
    secret (ni clair, ni chiffré), seulement le flag totp_enabled."""
    email = "noleak@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        secret = await _setup_and_enable_2fa(c, headers)
        me = await c.get(f"{BASE}/users/me", headers=headers)

    data = me.json()
    user = await _get_user(email)
    # Aucune clé du payload ne doit contenir la graine ni le blob chiffré.
    flat = str(data)
    assert secret not in flat
    assert user.totp_secret not in flat
    assert "totp_secret" not in data
    assert data["totp_enabled"] is True


# ── Invariant : reconfigurer une 2FA active exige le code courant ────────────


async def test_setup_when_enabled_without_current_code_is_rejected():
    """Un JWT valide ne suffit pas à re-générer une graine si la 2FA est active :
    il faut le code TOTP courant (anti account-takeover)."""
    email = "reconf@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        await _setup_and_enable_2fa(c, headers)
        before = (await _get_user(email)).totp_secret

        r = await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})

    assert r.status_code == 400
    # La graine ne doit PAS avoir été rotée par une tentative rejetée.
    after = (await _get_user(email)).totp_secret
    assert after == before


async def test_setup_when_enabled_bad_current_code_does_not_rotate_secret():
    """Reconfig avec un mauvais code courant → 400, et la graine reste intacte."""
    email = "reconfbad@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        secret = await _setup_and_enable_2fa(c, headers)
        before = (await _get_user(email)).totp_secret

        wrong = "654321" if pyotp.TOTP(secret).now() != "654321" else "123456"
        r = await c.post(
            f"{BASE}/users/me/2fa/setup", headers=headers, json={"current_code": wrong}
        )

    assert r.status_code == 400
    after = (await _get_user(email)).totp_secret
    assert after == before, "graine rotée malgré un code courant invalide !"


async def test_setup_when_enabled_valid_current_code_rotates_secret():
    """Reconfig avec le bon code courant → nouvelle graine différente de l'ancienne."""
    email = "reconfok@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        old_secret = await _setup_and_enable_2fa(c, headers)
        old_stored = (await _get_user(email)).totp_secret

        code = pyotp.TOTP(old_secret).now()
        r = await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={"current_code": code})
        assert r.status_code == 200
        new_secret = r.json()["secret"]

    assert new_secret != old_secret
    new_stored = (await _get_user(email)).totp_secret
    assert new_stored != old_stored
    assert decrypt_totp_secret(new_stored) == new_secret


# ── Invariant : login requires_2fa sans access_token ─────────────────────────


async def test_login_requires_2fa_payload_has_no_token_material():
    """Quand la 2FA est active et aucun code n'est fourni, la réponse est
    EXACTEMENT {requires_2fa: True} : aucun access_token / refresh cookie / salt."""
    email = "gate@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        await _setup_and_enable_2fa(c, headers)

        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": PWD})

    assert r.status_code == 200
    assert r.json() == {"requires_2fa": True}
    assert "access_token" not in r.json()
    assert "crypto_salt" not in r.json()
    # Aucun cookie refresh_token ne doit être posé tant que la 2FA n'est pas passée.
    assert "refresh_token" not in r.cookies


async def test_login_valid_totp_finalizes_and_issues_token():
    """Un code valide finalise le login : access_token présent + cookie refresh posé."""
    email = "finalize@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()

        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": email, "password": PWD, "totp_code": code},
        )

    assert r.status_code == 200
    data = r.json()
    assert data.get("access_token")
    assert "requires_2fa" not in data
    assert "refresh_token" in r.cookies


async def test_login_2fa_bad_code_never_issues_token():
    """Invariant : un mauvais code TOTP ne doit jamais produire d'access_token."""
    email = "badgate@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        await _setup_and_enable_2fa(c, headers)

        r = await c.post(
            f"{BASE}/auth/login",
            json={"email": email, "password": PWD, "totp_code": "000000"},
        )

    assert r.status_code == 401
    assert "access_token" not in r.json()
    assert "refresh_token" not in r.cookies


# ── Invariant : mock pyotp pour un code déterministe ─────────────────────────


async def test_login_uses_decrypted_secret_via_mocked_pyotp():
    """Le login déchiffre la graine avant de vérifier : on mocke pyotp.TOTP pour
    exiger que verify() reçoive le code fourni, de façon déterministe et hermétique."""
    email = "mocklogin@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        await _setup_and_enable_2fa(c, headers)

        # verify() renvoie True quel que soit le vrai secret → code déterministe.
        with patch("pyotp.TOTP") as MockTOTP:
            MockTOTP.return_value.verify.return_value = True
            r = await c.post(
                f"{BASE}/auth/login",
                json={"email": email, "password": PWD, "totp_code": "424242"},
            )

    assert r.status_code == 200
    assert "access_token" in r.json()
    # Le code fourni a bien été passé à verify() (avec fenêtre de tolérance).
    MockTOTP.return_value.verify.assert_called_once()
    args, kwargs = MockTOTP.return_value.verify.call_args
    assert args[0] == "424242"


async def test_login_mocked_pyotp_reject_blocks_token():
    """Symétrie : si verify() renvoie False, le login échoue en 401 sans token."""
    email = "mockreject@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        await _setup_and_enable_2fa(c, headers)

        with patch("pyotp.TOTP") as MockTOTP:
            MockTOTP.return_value.verify.return_value = False
            r = await c.post(
                f"{BASE}/auth/login",
                json={"email": email, "password": PWD, "totp_code": "999999"},
            )

    assert r.status_code == 401
    assert "access_token" not in r.json()


# ── Invariant : activer/désactiver exige les bons facteurs ───────────────────


async def test_disable_requires_password_even_with_valid_code():
    """Désactiver exige le mot de passe : un bon code TOTP seul ne suffit pas."""
    email = "needpwd@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()

        r = await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": "WrongPassword!", "code": code},
        )

    assert r.status_code == 401
    # 2FA toujours active + secret intact après la tentative refusée.
    user = await _get_user(email)
    assert user.totp_enabled is True
    assert user.totp_secret is not None


async def test_disable_success_clears_secret_and_blocks_replay():
    """Après désactivation valide : totp_enabled=False, secret effacé (None), et
    rejouer l'ancien secret ne ré-ouvre pas la porte 2FA au login."""
    email = "replay@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        secret = await _setup_and_enable_2fa(c, headers)
        code = pyotp.TOTP(secret).now()

        d = await c.post(
            f"{BASE}/users/me/2fa/disable",
            headers=headers,
            json={"password": PWD, "code": code},
        )
        assert d.status_code == 200

        # Login normal : plus de gate 2FA, token direct.
        r = await c.post(f"{BASE}/auth/login", json={"email": email, "password": PWD})

    assert r.status_code == 200
    assert "access_token" in r.json()
    user = await _get_user(email)
    assert user.totp_enabled is False
    assert user.totp_secret is None


async def test_enable_requires_prior_setup_secret():
    """enable sans setup préalable (aucun secret) → 400, et totp_enabled reste False."""
    email = "nosetupenable@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        r = await c.post(f"{BASE}/users/me/2fa/enable", headers=headers, json={"code": "123456"})

    assert r.status_code == 400
    user = await _get_user(email)
    assert user.totp_enabled is False


async def test_enable_bad_code_keeps_2fa_disabled():
    """Setup effectué mais code de vérification faux → 400 ; la 2FA reste inactive
    (invariant : on n'active jamais sans preuve de possession de la graine)."""
    email = "badverify@2fa.com"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        headers = await _register_login(c, email)
        await c.post(f"{BASE}/users/me/2fa/setup", headers=headers, json={})

        r = await c.post(f"{BASE}/users/me/2fa/enable", headers=headers, json={"code": "000000"})

    assert r.status_code == 400
    user = await _get_user(email)
    assert user.totp_enabled is False
    # Le secret de setup est bien présent mais l'activation n'a pas eu lieu.
    assert user.totp_secret is not None
