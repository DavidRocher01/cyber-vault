"""add user crypto_salt

Revision ID: d7e2f3a4b5c6
Revises: b8c4d2e9f1a3
Create Date: 2026-06-05 11:00:00.000000

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d7e2f3a4b5c6"
down_revision: str | None = "b8c4d2e9f1a3"
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
