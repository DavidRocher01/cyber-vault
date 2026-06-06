"""vault title nullable for zero-knowledge

Revision ID: 0fda8d4857ac
Revises: e9f1a2b3c4d5
Create Date: 2026-06-06 12:10:18.720315

Zero-knowledge vault: the client no longer sends plaintext title/username/url/
notes — only the *_encrypted blobs. `title` was the last plaintext column still
NOT NULL, so it must become nullable for new (encrypted-only) items.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0fda8d4857ac"
down_revision: str | None = "e9f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "vault_items",
        "title",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "vault_items",
        "title",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
