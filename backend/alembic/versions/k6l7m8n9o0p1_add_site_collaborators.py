"""add site_collaborators

Revision ID: k6l7m8n9o0p1
Revises: j5k6l7m8n9o0
Create Date: 2026-05-19
"""

import sqlalchemy as sa

from alembic import op

revision = "k6l7m8n9o0p1"
down_revision = "j5k6l7m8n9o0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "site_collaborators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.Integer(), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("invite_token", sa.String(64), nullable=False),
        sa.Column("invited_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["site_id"], ["sites.id"]),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "email", name="uq_collab_site_email"),
        sa.UniqueConstraint("invite_token"),
    )
    op.create_index("ix_site_collaborators_id", "site_collaborators", ["id"])
    op.create_index("ix_site_collaborators_site_id", "site_collaborators", ["site_id"])
    op.create_index("ix_site_collaborators_owner_user_id", "site_collaborators", ["owner_user_id"])
    op.create_index("ix_site_collaborators_invite_token", "site_collaborators", ["invite_token"])


def downgrade() -> None:
    op.drop_index("ix_site_collaborators_invite_token", table_name="site_collaborators")
    op.drop_index("ix_site_collaborators_owner_user_id", table_name="site_collaborators")
    op.drop_index("ix_site_collaborators_site_id", table_name="site_collaborators")
    op.drop_index("ix_site_collaborators_id", table_name="site_collaborators")
    op.drop_table("site_collaborators")
