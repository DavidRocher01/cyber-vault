"""add rssi_clients table and rssi_client_id on sites

Revision ID: f1a2b3c4d5e6
Revises: c3d4e5f6a7b8
Create Date: 2026-05-19
"""

import sqlalchemy as sa

from alembic import op

revision = "f1a2b3c4d5e6"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rssi_clients",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "consultant_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("description", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sites",
        sa.Column(
            "rssi_client_id",
            sa.Integer(),
            sa.ForeignKey("rssi_clients.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_sites_rssi_client_id", "sites", ["rssi_client_id"])


def downgrade():
    op.drop_index("ix_sites_rssi_client_id", "sites")
    op.drop_column("sites", "rssi_client_id")
    op.drop_table("rssi_clients")
