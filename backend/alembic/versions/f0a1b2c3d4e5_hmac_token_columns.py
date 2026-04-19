"""hash_token upgraded to HMAC-SHA256 — resize token columns to 64 chars

Revision ID: f0a1b2c3d4e5
Revises: e8f9a0b1c2d3
Create Date: 2026-04-19

The token hashing scheme changed from bare SHA-256 to HMAC-SHA256 (keyed with
SECRET_KEY).  All existing hashed tokens are therefore invalid and are deleted
here so users receive a clean logout instead of a broken verification.

Column size is reduced from 512 → 64 chars (HMAC-SHA256 hex is exactly 64).
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Invalidate all existing tokens (old SHA-256 hashes no longer verify)
    op.execute("DELETE FROM refresh_tokens")
    op.execute("DELETE FROM password_reset_tokens")

    # 2. Resize token columns — HMAC-SHA256 hexdigest is always 64 chars
    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sa.String(512),
            type_=sa.String(64),
            existing_nullable=False,
        )

    with op.batch_alter_table("password_reset_tokens") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sa.String(512),
            type_=sa.String(64),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("password_reset_tokens") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sa.String(64),
            type_=sa.String(512),
            existing_nullable=False,
        )

    with op.batch_alter_table("refresh_tokens") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sa.String(64),
            type_=sa.String(512),
            existing_nullable=False,
        )
