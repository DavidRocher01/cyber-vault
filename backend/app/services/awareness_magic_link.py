"""
Magic-link authentication for awareness learners.

Flow:
  1. POST /awareness/auth/magic-link  → generate token, send email
  2. GET  /awareness/auth/verify?token=...  → validate token, return session JWT
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.awareness_learner import AwarenessLearner

_TOKEN_BYTES = 32
_TOKEN_TTL_MINUTES = 15
_SESSION_TTL_HOURS = 24


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_magic_token() -> tuple[str, str]:
    """Return (raw_token, hashed_token). Store only the hash in DB."""
    raw = secrets.token_urlsafe(_TOKEN_BYTES)
    return raw, _hash_token(raw)


def create_learner_jwt(learner: AwarenessLearner) -> str:
    expire = datetime.now(UTC) + timedelta(hours=_SESSION_TTL_HOURS)
    payload = {
        "sub": str(learner.id),
        "org": learner.organization_id,
        "type": "awareness_learner",
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_learner_jwt(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "awareness_learner":
            return None
        return payload
    except JWTError:
        return None


async def issue_magic_link(
    db: AsyncSession, email: str, organization_id: int
) -> tuple[AwarenessLearner, str] | None:
    """
    Find learner by email+org, generate a magic token, store its hash.
    Returns (learner, raw_token) or None if learner not found.
    """
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.email == email,
            AwarenessLearner.organization_id == organization_id,
            AwarenessLearner.is_active == True,
        )
    )
    learner = result.scalar_one_or_none()
    if learner is None:
        return None

    raw, hashed = generate_magic_token()
    learner.access_token_hash = hashed
    learner.access_token_expires_at = datetime.now(UTC) + timedelta(minutes=_TOKEN_TTL_MINUTES)
    await db.commit()
    return learner, raw


async def verify_magic_link(db: AsyncSession, raw_token: str) -> AwarenessLearner | None:
    """
    Validate a raw magic token. On success: clear the token, update last_login_at.
    Returns the learner or None if token is invalid/expired.
    """
    hashed = _hash_token(raw_token)
    result = await db.execute(
        select(AwarenessLearner).where(
            AwarenessLearner.access_token_hash == hashed,
            AwarenessLearner.is_active == True,
        )
    )
    learner = result.scalar_one_or_none()
    if learner is None:
        return None

    if learner.access_token_expires_at and learner.access_token_expires_at < datetime.now(UTC):
        return None

    learner.access_token_hash = None
    learner.access_token_expires_at = None
    learner.last_login_at = datetime.now(UTC)
    await db.commit()
    return learner
