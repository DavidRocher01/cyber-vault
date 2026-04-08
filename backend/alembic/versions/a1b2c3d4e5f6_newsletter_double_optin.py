"""newsletter double opt-in: add confirmation_token, confirmed_at, set is_active default False

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-04-08 16:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "newsletter_subscribers",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "newsletter_subscribers",
        sa.Column("confirmation_token", sa.String(512), nullable=True),
    )
    op.create_unique_constraint("uq_newsletter_confirmation_token", "newsletter_subscribers", ["confirmation_token"])
    op.create_index("ix_newsletter_confirmation_token", "newsletter_subscribers", ["confirmation_token"])
    # Existing subscribers are already confirmed — mark them active & set confirmed_at
    op.execute(
        "UPDATE newsletter_subscribers SET confirmed_at = subscribed_at WHERE is_active = TRUE"
    )


def downgrade() -> None:
    op.drop_index("ix_newsletter_confirmation_token", "newsletter_subscribers")
    op.drop_constraint("uq_newsletter_confirmation_token", "newsletter_subscribers", type_="unique")
    op.drop_column("newsletter_subscribers", "confirmation_token")
    op.drop_column("newsletter_subscribers", "confirmed_at")
