"""add app_settings table

Revision ID: e8f9a0b1c2d3
Revises: f7a8b9c0d1e2
Create Date: 2026-04-17

Persistent key/value store for app-level config (e.g. newsletter_edition counter).
Replaces in-memory global _newsletter_edition in scheduler.py which reset on restart.
"""
import sqlalchemy as sa
from alembic import op

revision = "e8f9a0b1c2d3"
down_revision = "f7a8b9c0d1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value_int", sa.Integer(), nullable=False, server_default="0"),
    )
    # Seed the newsletter edition counter starting at 1
    op.execute("INSERT INTO app_settings (key, value_int) VALUES ('newsletter_edition', 1)")


def downgrade() -> None:
    op.drop_table("app_settings")
