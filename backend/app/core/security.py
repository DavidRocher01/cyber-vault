import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import settings

REFRESH_TOKEN_EXPIRE_DAYS = 30


def _bcrypt_bytes(password: str) -> bytes:
    # bcrypt >= 4/5 lève ValueError si le mot de passe dépasse 72 octets, alors que
    # les versions historiques tronquaient silencieusement. On tronque à 72 octets
    # pour éviter un 500 sur les mots de passe longs ET rester compatible avec les
    # hash déjà en base (calculés sur les 72 premiers octets par l'ancien bcrypt).
    return password.encode()[:72]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_bcrypt_bytes(password), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(_bcrypt_bytes(plain_password), hashed_password.encode())


# Hash bcrypt jetable, calcule une seule fois au demarrage. Sert a egaliser le
# temps de reponse d'un login sur un email INEXISTANT avec celui d'un email
# existant + mauvais mot de passe : sans cela, l'absence de checkpw rend la
# reponse "pas de compte" mesurablement plus rapide et permet d'enumerer les
# comptes par timing (S-9).
_DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"timing-attack-dummy", bcrypt.gensalt()).decode()


def dummy_verify_password() -> None:
    """Consomme le meme temps CPU qu'un verify_password reel (anti-enumeration).

    Le cout de bcrypt.checkpw ne depend que du facteur de cout du hash, pas de
    l'entree : comparer un mot de passe fixe au hash jetable prend le meme temps
    qu'une verification legitime.
    """
    bcrypt.checkpw(b"timing-attack-dummy", _DUMMY_PASSWORD_HASH.encode())


def create_access_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # "type": "access" empêche qu'un autre JWT signé avec le même secret
    # (ex: token learner awareness, type="awareness_learner") soit accepté ici.
    payload = {"sub": subject, "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # Rejette tout token dont le type n'est pas exactement "access"
        # (anti-confusion de types : usurpation de compte via token learner).
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except jwt.PyJWTError:
        return None


def create_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def hash_token(raw_token: str) -> str:
    """HMAC-SHA256 of a token for safe DB storage.
    Using SECRET_KEY as the HMAC key means a DB dump alone cannot be used to
    build rainbow tables — the attacker also needs the application secret.
    Output is always 64 hex chars.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        raw_token.encode(),
        hashlib.sha256,
    ).hexdigest()


def make_unsubscribe_token(email: str) -> str:
    """Deterministic HMAC-SHA256 unsubscribe token derived from email + SECRET_KEY.
    Recomputable at any time (no raw value to store), and constant across newsletter
    sends so old links remain valid indefinitely.
    Output is 64 hex chars.
    """
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"newsletter:unsub:{email}".encode(),
        hashlib.sha256,
    ).hexdigest()
