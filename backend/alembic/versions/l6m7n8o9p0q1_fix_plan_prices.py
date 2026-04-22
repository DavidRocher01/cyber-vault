"""Fix plan prices to correct values (cents)

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-04-22

Corrects plan prices that were seeded with wrong values in production.
Starter: 9,90 € (990), Pro: 39,90 € (3990), Business: 49,90 € (4990).
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, None] = "k5l6m7n8o9p0"
branch_labels = None
depends_on = None

CORRECT_PRICES = {
    "starter":  990,   # 9,90 €
    "pro":      3990,  # 39,90 €
    "business": 4990,  # 49,90 €
}


def upgrade() -> None:
    conn = op.get_bind()
    for plan_name, price_eur in CORRECT_PRICES.items():
        conn.execute(
            sa.text("UPDATE plans SET price_eur = :price WHERE name = :name"),
            {"price": price_eur, "name": plan_name},
        )


def downgrade() -> None:
    pass
