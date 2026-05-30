"""add brand_profiles

Revision ID: j5k6l7m8n9o0
Revises: i4j5k6l7m8n9
Create Date: 2026-05-19
"""

import sqlalchemy as sa

from alembic import op

revision = "j5k6l7m8n9o0"
down_revision = "i4j5k6l7m8n9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "brand_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("accent_color", sa.String(7), nullable=False, server_default="#06b6d4"),
        sa.Column("logo_b64", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_brand_profile_user"),
    )
    op.create_index("ix_brand_profiles_id", "brand_profiles", ["id"])
    op.create_index("ix_brand_profiles_user_id", "brand_profiles", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_brand_profiles_user_id", table_name="brand_profiles")
    op.drop_index("ix_brand_profiles_id", table_name="brand_profiles")
    op.drop_table("brand_profiles")
