"""Update Stripe price IDs from test to live

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-04-22

Overwrites test price IDs with live price IDs created on 2026-04-22.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "m7n8o9p0q1r2"
down_revision: Union[str, None] = "l6m7n8o9p0q1"
branch_labels = None
depends_on = None

LIVE_PRICE_IDS = {
    "starter":  "price_1TOzSg1kFVtkWldS7qBgnmh6",
    "pro":      "price_1TOzSk1kFVtkWldSj1Z5U49V",
    "business": "price_1TOzSk1kFVtkWldS4RJ2u8pf",
}


def upgrade() -> None:
    conn = op.get_bind()
    for plan_name, price_id in LIVE_PRICE_IDS.items():
        conn.execute(
            sa.text("UPDATE plans SET stripe_price_id = :price_id WHERE name = :name"),
            {"price_id": price_id, "name": plan_name},
        )


def downgrade() -> None:
    pass
