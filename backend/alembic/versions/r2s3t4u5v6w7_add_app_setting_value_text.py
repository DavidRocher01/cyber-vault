"""Add value_text column to app_settings

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-05-16
"""

import sqlalchemy as sa

from alembic import op

revision: str = "r2s3t4u5v6w7"
down_revision: str | None = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("app_settings", sa.Column("value_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_settings", "value_text")
