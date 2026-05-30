"""add consultant profile fields

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-05-22
"""

import sqlalchemy as sa

from alembic import op

revision = "r3s4t5u6v7w8"
down_revision = "q2r3s4t5u6v7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("company_name", sa.String(150), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
    op.drop_column("users", "company_name")
    op.drop_column("users", "display_name")
