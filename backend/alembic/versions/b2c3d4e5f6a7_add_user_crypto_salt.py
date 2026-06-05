"""add user crypto_salt

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-05 11:00:00.000000

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add nullable first, backfill random salt for existing users, then set NOT NULL
    op.add_column("users", sa.Column("crypto_salt", sa.LargeBinary(32), nullable=True))

    connection = op.get_bind()
    users = connection.execute(sa.text("SELECT id FROM users WHERE crypto_salt IS NULL")).fetchall()
    for (user_id,) in users:
        salt = os.urandom(32)
        connection.execute(
            sa.text("UPDATE users SET crypto_salt = :salt WHERE id = :id"),
            {"salt": salt, "id": user_id},
        )

    op.alter_column("users", "crypto_salt", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "crypto_salt")
