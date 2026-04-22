"""Update Stripe price IDs to live tax_behavior=exclusive prices

Revision ID: o9p0q1r2s3t4
Revises: n8o9p0q1r2s3
Create Date: 2026-04-22

Replaces previous price IDs with live exclusive-tax prices
(created in Stripe live mode) so clients pay HT + TVA 20% on top.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "o9p0q1r2s3t4"
down_revision: Union[str, None] = "n8o9p0q1r2s3"
branch_labels = None
depends_on = None

LIVE_EXCLUSIVE_PRICE_IDS = {
    "starter":  "price_1TP39P1kFVtkWldSpyPHATaJ",
    "pro":      "price_1TP38J1kFVtkWldSODGNBTD8",
    "business": "price_1TP38n1kFVtkWldSLUJ1zRpi",
}


def upgrade() -> None:
    conn = op.get_bind()
    for plan_name, price_id in LIVE_EXCLUSIVE_PRICE_IDS.items():
        conn.execute(
            sa.text("UPDATE plans SET stripe_price_id = :price_id WHERE name = :name"),
            {"price_id": price_id, "name": plan_name},
        )


def downgrade() -> None:
    pass
