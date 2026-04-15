"""add notification preferences to users

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-04-15 10:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e6f7a8b9c0"
down_revision: Union[str, None] = "c4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("notif_scan_done", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("users", sa.Column("notif_scan_critical", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("users", sa.Column("notif_url_scan_done", sa.Boolean(), nullable=False, server_default="true"))
    op.add_column("users", sa.Column("notif_code_scan_done", sa.Boolean(), nullable=False, server_default="true"))


def downgrade() -> None:
    op.drop_column("users", "notif_code_scan_done")
    op.drop_column("users", "notif_url_scan_done")
    op.drop_column("users", "notif_scan_critical")
    op.drop_column("users", "notif_scan_done")
