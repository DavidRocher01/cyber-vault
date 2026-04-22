"""Update Stripe price IDs to tax_behavior=exclusive (HT + TVA on top)

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-04-22

Replaces inclusive-tax price IDs with new exclusive-tax price IDs
so clients are charged HT + TVA 20% on top.
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "n8o9p0q1r2s3"
down_revision: Union[str, None] = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None

EXCLUSIVE_PRICE_IDS = {
    "starter":  "price_1TP2db22WVBQ28elfBoc3AOZ",
    "pro":      "price_1TP2ZZ22WVBQ28elz9r3Cknm",
    "business": "price_1TOwxP22WVBQ28elsWUTRnKN",
}


def upgrade() -> None:
    conn = op.get_bind()
    for plan_name, price_id in EXCLUSIVE_PRICE_IDS.items():
        conn.execute(
            sa.text("UPDATE plans SET stripe_price_id = :price_id WHERE name = :name"),
            {"price_id": price_id, "name": plan_name},
        )


def downgrade() -> None:
    pass
