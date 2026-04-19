"""add image_url to newsletter_schedule_items

Revision ID: g1h2i3j4k5l6
Revises: d2e3f4a5b6c7
Create Date: 2026-04-19 00:00:00.000000

"""
from typing import Union
import sqlalchemy as sa
from alembic import op

revision: str = "g1h2i3j4k5l6"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "newsletter_schedule_items",
        sa.Column("image_url", sa.String(1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("newsletter_schedule_items", "image_url")
