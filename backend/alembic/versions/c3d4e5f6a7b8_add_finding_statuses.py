"""add finding_statuses table

Revision ID: c3d4e5f6a7b8
Revises: z0a1b2c3d4e5
Create Date: 2026-05-19

"""

import sqlalchemy as sa

from alembic import op

revision = "c3d4e5f6a7b8"
down_revision = "z0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "finding_statuses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "site_id",
            sa.Integer(),
            sa.ForeignKey("sites.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("module_key", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="todo"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("site_id", "module_key", name="uq_finding_status_site_module"),
    )
    op.create_index("ix_finding_statuses_site_id", "finding_statuses", ["site_id"])


def downgrade() -> None:
    op.drop_index("ix_finding_statuses_site_id", "finding_statuses")
    op.drop_table("finding_statuses")
