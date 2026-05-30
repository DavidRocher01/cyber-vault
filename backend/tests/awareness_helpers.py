"""Shared test helpers for awareness module tests."""

from __future__ import annotations


async def get_awareness_magic_token(learner_email: str, org_id: int) -> str:
    """
    Bypass the magic-link HTTP endpoint (which no longer returns the raw token
    for security reasons) and call issue_magic_link() directly to obtain the
    raw token for use in tests.
    """
    import app.core.database as _db_module
    from app.services.awareness_magic_link import issue_magic_link

    async with _db_module.AsyncSessionLocal() as db:
        result = await issue_magic_link(db, learner_email, org_id)
        if result is None:
            raise ValueError(f"Learner {learner_email} not found in org {org_id}")
        _, raw_token = result
        return raw_token
