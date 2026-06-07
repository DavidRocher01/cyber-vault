"""Chiffrement au repos des secrets TOTP (graines 2FA).

La graine TOTP est une donnée sensible : un dump DB ne doit pas permettre de
régénérer les codes 2FA. On la chiffre via Fernet (AES-CBC + HMAC) avec une clé
dérivée de SECRET_KEY.

`decrypt_totp_secret` retombe sur la valeur brute si ce n'est pas un token
Fernet valide : compatibilité avec les graines déjà stockées en clair avant
l'introduction du chiffrement (elles continuent de fonctionner, et sont
ré-écrites chiffrées au prochain setup).
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.SECRET_KEY.encode()).digest())
    return Fernet(key)


def encrypt_totp_secret(secret: str) -> str:
    return _fernet().encrypt(secret.encode()).decode()


def decrypt_totp_secret(stored: str) -> str:
    try:
        return _fernet().decrypt(stored.encode()).decode()
    except (InvalidToken, ValueError):
        # Graine legacy stockée en clair (avant chiffrement at-rest) — utilisée telle quelle.
        return stored
