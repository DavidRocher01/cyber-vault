"""newsletter double opt-in: add confirmation_token, confirmed_at, set is_active default False

Revision ID: c1d2e3f4a5b6
Revises: d397692772ea
Create Date: 2026-04-08 16:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "d397692772ea"
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
