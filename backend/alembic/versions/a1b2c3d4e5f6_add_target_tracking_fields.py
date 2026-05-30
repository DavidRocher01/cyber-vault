"""add per-target scenario_key and event timestamps

Revision ID: phish_target_ts_2026
Revises: m8n9o0p1q2r3
Create Date: 2026-05-27

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "phish_target_ts_2026"
down_revision: str | None = "m8n9o0p1q2r3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "phishing_targets",
        sa.Column("scenario_key", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "phishing_targets",
        sa.Column("email_sent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "phishing_targets",
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "phishing_targets",
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "phishing_targets",
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("phishing_targets", "submitted_at")
    op.drop_column("phishing_targets", "clicked_at")
    op.drop_column("phishing_targets", "opened_at")
    op.drop_column("phishing_targets", "email_sent_at")
    op.drop_column("phishing_targets", "scenario_key")
