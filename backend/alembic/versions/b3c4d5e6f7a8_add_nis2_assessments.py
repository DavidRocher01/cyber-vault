"""add nis2_assessments table

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-04-13 12:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "nis2_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("items_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_nis2_assessments_user_id"),
    )
    op.create_index("ix_nis2_assessments_id", "nis2_assessments", ["id"], unique=False)
    op.create_index("ix_nis2_assessments_user_id", "nis2_assessments", ["user_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_nis2_assessments_user_id", table_name="nis2_assessments")
    op.drop_index("ix_nis2_assessments_id", table_name="nis2_assessments")
    op.drop_table("nis2_assessments")
