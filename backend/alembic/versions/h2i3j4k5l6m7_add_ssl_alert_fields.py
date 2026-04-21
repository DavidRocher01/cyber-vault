"""add ssl alert fields to sites and notif_ssl_expiry to users

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-04-21 00:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "h2i3j4k5l6m7"
down_revision: Union[str, None] = "g1h2i3j4k5l6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sites", sa.Column("ssl_alert_threshold", sa.Integer(), nullable=True))
    op.add_column("sites", sa.Column("ssl_alert_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("notif_ssl_expiry", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("users", "notif_ssl_expiry")
    op.drop_column("sites", "ssl_alert_sent_at")
    op.drop_column("sites", "ssl_alert_threshold")
