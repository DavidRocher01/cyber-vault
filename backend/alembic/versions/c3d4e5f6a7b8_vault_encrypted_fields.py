"""vault encrypted fields

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("vault_items", sa.Column("title_encrypted", sa.Text, nullable=True))
    op.add_column("vault_items", sa.Column("username_encrypted", sa.Text, nullable=True))
    op.add_column("vault_items", sa.Column("url_encrypted", sa.Text, nullable=True))
    op.add_column("vault_items", sa.Column("notes_encrypted", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("vault_items", "notes_encrypted")
    op.drop_column("vault_items", "url_encrypted")
    op.drop_column("vault_items", "username_encrypted")
    op.drop_column("vault_items", "title_encrypted")
