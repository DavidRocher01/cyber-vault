"""widen totp_secret for at-rest encryption

Revision ID: b7f3e1a9c2d4
Revises: 0fda8d4857ac
Create Date: 2026-06-07 13:30:00.000000

La graine TOTP est désormais chiffrée au repos (Fernet). Le token chiffré
(~140 caractères) dépasse l'ancienne colonne String(64) -> élargie à 255.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7f3e1a9c2d4"
down_revision: str | None = "0fda8d4857ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "totp_secret",
        existing_type=sa.String(length=64),
        type_=sa.String(length=255),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "totp_secret",
        existing_type=sa.String(length=255),
        type_=sa.String(length=64),
        existing_nullable=True,
    )
