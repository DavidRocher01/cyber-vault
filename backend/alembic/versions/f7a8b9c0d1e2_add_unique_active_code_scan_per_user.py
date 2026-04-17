"""add unique active code scan per user

Revision ID: f7a8b9c0d1e2
Revises: d5e6f7a8b9c0
Create Date: 2026-04-17

Prevents concurrent pending/running code scans per user at the DB level,
closing the check-then-insert race condition in _check_no_running_scan.
"""
from alembic import op

revision = "f7a8b9c0d1e2"
down_revision = "d5e6f7a8b9c0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Partial unique index: at most one active (pending or running) code scan per user.
    # PostgreSQL and SQLite 3.8.9+ both support partial indexes.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_code_scan_active_per_user
        ON code_scans (user_id)
        WHERE status IN ('pending', 'running')
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_code_scan_active_per_user")
