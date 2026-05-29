"""Enhance rssi_clients with full spec fields and add is_rssi_consultant to users

Revision ID: n9o0p1q2r3s4
Revises: m8n9o0p1q2r3
Create Date: 2026-05-22
"""

import sqlalchemy as sa

from alembic import op

revision = "n9o0p1q2r3s4"
down_revision = "m8n9o0p1q2r3"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rssi_clients", sa.Column("formula", sa.String(20), nullable=True))
    op.add_column("rssi_clients", sa.Column("monthly_amount", sa.Numeric(10, 2), nullable=True))
    op.add_column("rssi_clients", sa.Column("contract_start_date", sa.Date(), nullable=True))
    op.add_column("rssi_clients", sa.Column("contract_renewal_at", sa.Date(), nullable=True))
    op.add_column(
        "rssi_clients",
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
    )
    op.add_column("rssi_clients", sa.Column("notion_workspace_url", sa.String(500), nullable=True))
    op.add_column("rssi_clients", sa.Column("pipedrive_deal_id", sa.String(50), nullable=True))
    op.add_column("rssi_clients", sa.Column("pennylane_customer_id", sa.String(50), nullable=True))
    op.add_column("rssi_clients", sa.Column("extra_data", sa.Text(), nullable=True))
    op.add_column(
        "rssi_clients",
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("is_rssi_consultant", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade():
    op.drop_column("users", "is_rssi_consultant")
    op.drop_column("rssi_clients", "updated_at")
    op.drop_column("rssi_clients", "extra_data")
    op.drop_column("rssi_clients", "pennylane_customer_id")
    op.drop_column("rssi_clients", "pipedrive_deal_id")
    op.drop_column("rssi_clients", "notion_workspace_url")
    op.drop_column("rssi_clients", "status")
    op.drop_column("rssi_clients", "contract_renewal_at")
    op.drop_column("rssi_clients", "contract_start_date")
    op.drop_column("rssi_clients", "monthly_amount")
    op.drop_column("rssi_clients", "formula")
