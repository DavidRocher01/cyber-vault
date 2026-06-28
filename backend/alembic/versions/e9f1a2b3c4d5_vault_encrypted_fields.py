"""vault encrypted fields

Revision ID: e9f1a2b3c4d5
Revises: d7e2f3a4b5c6
Create Date: 2026-06-05 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e9f1a2b3c4d5"
down_revision: str | None = "d7e2f3a4b5c6"
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
