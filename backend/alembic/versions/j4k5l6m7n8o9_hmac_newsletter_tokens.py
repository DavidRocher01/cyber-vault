"""HMAC-SHA256 newsletter token columns

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-04-22

- confirmation_token : now stores HMAC-SHA256 hash (64 chars) of the raw token
  sent in the confirmation email URL. Pending confirmations are invalidated and
  cleared; users can re-subscribe to receive a fresh link.
- unsubscribe_token  : migrated to a deterministic HMAC-SHA256 derived from
  email + SECRET_KEY. Old random tokens (String 512) are replaced; old
  unsubscribe links from previously sent newsletters will no longer work, but
  new newsletter sends always recompute the token from email.
- Both columns are resized 512 → 64 chars.
"""

import hashlib
import hmac
import os
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "j4k5l6m7n8o9"
down_revision: Union[str, None] = "i3j4k5l6m7n8"
branch_labels = None
depends_on = None


def _make_unsubscribe_token(email: str, secret_key: str) -> str:
    return hmac.new(
        secret_key.encode(),
        f"newsletter:unsub:{email}".encode(),
        hashlib.sha256,
    ).hexdigest()


def upgrade() -> None:
    secret_key = os.environ.get("SECRET_KEY", "")
    conn = op.get_bind()

    # 1. Invalidate all pending confirmation tokens (old links in inboxes no
    #    longer match — subscribers must re-subscribe to get a fresh link).
    conn.execute(sa.text("UPDATE newsletter_subscribers SET confirmation_token = NULL"))

    # 2. Recompute unsubscribe tokens as deterministic HMAC of email.
    rows = conn.execute(
        sa.text("SELECT id, email FROM newsletter_subscribers")
    ).fetchall()
    for row in rows:
        new_token = _make_unsubscribe_token(row.email, secret_key)
        conn.execute(
            sa.text("UPDATE newsletter_subscribers SET unsubscribe_token = :t WHERE id = :id"),
            {"t": new_token, "id": row.id},
        )

    # 3. Resize columns 512 → 64 chars.
    with op.batch_alter_table("newsletter_subscribers") as batch_op:
        batch_op.alter_column(
            "confirmation_token",
            existing_type=sa.String(512),
            type_=sa.String(64),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "unsubscribe_token",
            existing_type=sa.String(512),
            type_=sa.String(64),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("newsletter_subscribers") as batch_op:
        batch_op.alter_column(
            "unsubscribe_token",
            existing_type=sa.String(64),
            type_=sa.String(512),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "confirmation_token",
            existing_type=sa.String(64),
            type_=sa.String(512),
            existing_nullable=True,
        )
