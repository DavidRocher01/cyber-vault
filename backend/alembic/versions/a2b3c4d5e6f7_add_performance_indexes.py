"""add performance indexes on status and composite columns

Revision ID: a2b3c4d5e6f7
Revises: e1f2a3b4c5d6, f6a7b8c9d0e1
Create Date: 2026-04-13 00:00:00.000000

"""
from typing import Union

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, tuple] = ("e1f2a3b4c5d6", "f6a7b8c9d0e1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── scans ──────────────────────────────────────────────────────────────
    op.create_index("ix_scans_status", "scans", ["status"], unique=False)
    op.create_index("ix_scans_site_id_status", "scans", ["site_id", "status"], unique=False)
    op.create_index("ix_scans_site_id_finished_at", "scans", ["site_id", "finished_at"], unique=False)

    # ── url_scans ──────────────────────────────────────────────────────────
    op.create_index("ix_url_scans_status", "url_scans", ["status"], unique=False)
    op.create_index("ix_url_scans_user_id_status", "url_scans", ["user_id", "status"], unique=False)
    op.create_index("ix_url_scans_user_id_created_at", "url_scans", ["user_id", "created_at"], unique=False)

    # ── code_scans ─────────────────────────────────────────────────────────
    op.create_index("ix_code_scans_status", "code_scans", ["status"], unique=False)
    op.create_index("ix_code_scans_user_id_status", "code_scans", ["user_id", "status"], unique=False)
    op.create_index("ix_code_scans_user_id_created_at", "code_scans", ["user_id", "created_at"], unique=False)

    # ── subscriptions ──────────────────────────────────────────────────────
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"], unique=False)
    op.create_index("ix_subscriptions_user_id_status", "subscriptions", ["user_id", "status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_subscriptions_user_id_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_code_scans_user_id_created_at", table_name="code_scans")
    op.drop_index("ix_code_scans_user_id_status", table_name="code_scans")
    op.drop_index("ix_code_scans_status", table_name="code_scans")
    op.drop_index("ix_url_scans_user_id_created_at", table_name="url_scans")
    op.drop_index("ix_url_scans_user_id_status", table_name="url_scans")
    op.drop_index("ix_url_scans_status", table_name="url_scans")
    op.drop_index("ix_scans_site_id_finished_at", table_name="scans")
    op.drop_index("ix_scans_site_id_status", table_name="scans")
    op.drop_index("ix_scans_status", table_name="scans")
