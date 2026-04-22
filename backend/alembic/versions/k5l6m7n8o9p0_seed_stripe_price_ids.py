"""Seed Stripe test price IDs into plans table

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-04-22

Injects the Stripe test price IDs created on 2026-04-22 into the plans table.
When switching to live mode, run seed_plans.py again with the live price IDs.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "k5l6m7n8o9p0"
down_revision: Union[str, None] = "j4k5l6m7n8o9"
branch_labels = None
depends_on = None

PRICE_IDS = {
    "starter":  "price_1TOzSg1kFVtkWldS7qBgnmh6",
    "pro":      "price_1TOzSk1kFVtkWldSj1Z5U49V",
    "business": "price_1TOzSk1kFVtkWldS4RJ2u8pf",
}


def upgrade() -> None:
    conn = op.get_bind()
    for plan_name, price_id in PRICE_IDS.items():
        conn.execute(
            sa.text(
                "UPDATE plans SET stripe_price_id = :price_id WHERE name = :name"
            ),
            {"price_id": price_id, "name": plan_name},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for plan_name in PRICE_IDS:
        conn.execute(
            sa.text("UPDATE plans SET stripe_price_id = '' WHERE name = :name"),
            {"name": plan_name},
        )
