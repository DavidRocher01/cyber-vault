"""add public_scans table

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-04-21 12:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "i3j4k5l6m7n8"
down_revision: Union[str, None] = "h2i3j4k5l6m7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_token", sa.String(64), nullable=False),
        sa.Column("target_url", sa.String(512), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("overall_status", sa.String(20), nullable=True),
        sa.Column("results_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_public_scans_id", "public_scans", ["id"])
    op.create_index("ix_public_scans_token", "public_scans", ["session_token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_public_scans_token", table_name="public_scans")
    op.drop_index("ix_public_scans_id", table_name="public_scans")
    op.drop_table("public_scans")
