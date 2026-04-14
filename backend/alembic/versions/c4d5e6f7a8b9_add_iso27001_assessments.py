"""add iso27001_assessments table

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-04-14 12:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, None] = "b3c4d5e6f7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iso27001_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("items_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_iso27001_assessments_user_id"),
    )
    op.create_index("ix_iso27001_assessments_id", "iso27001_assessments", ["id"], unique=False)
    op.create_index("ix_iso27001_assessments_user_id", "iso27001_assessments", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_iso27001_assessments_user_id", table_name="iso27001_assessments")
    op.drop_index("ix_iso27001_assessments_id", table_name="iso27001_assessments")
    op.drop_table("iso27001_assessments")
