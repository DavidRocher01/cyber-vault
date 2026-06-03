"""reprice_plans_v2

Revision ID: 6f5b7d420f72
Revises: 977a962a96fb
Create Date: 2026-06-03 07:45:59.191478

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6f5b7d420f72"
down_revision: str | None = "977a962a96fb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE plans SET display_name='Surveillance Starter', price_eur=1490,"
        " max_sites=1, scan_interval_days=7, stripe_price_id='' WHERE name='starter'"
    )
    op.execute(
        "UPDATE plans SET display_name='Surveillance Pro', price_eur=4900,"
        " max_sites=5, scan_interval_days=7, stripe_price_id='' WHERE name='pro'"
    )
    op.execute(
        "UPDATE plans SET display_name='Surveillance Business', price_eur=14900,"
        " max_sites=15, scan_interval_days=1, stripe_price_id='' WHERE name='business'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE plans SET display_name='Starter', price_eur=990,"
        " max_sites=1, scan_interval_days=30,"
        " stripe_price_id='price_1TP39P1kFVtkWldSpyPHATaJ' WHERE name='starter'"
    )
    op.execute(
        "UPDATE plans SET display_name='Pro', price_eur=3990,"
        " max_sites=3, scan_interval_days=7,"
        " stripe_price_id='price_1TP38J1kFVtkWldSODGNBTD8' WHERE name='pro'"
    )
    op.execute(
        "UPDATE plans SET display_name='Business', price_eur=4990,"
        " max_sites=10, scan_interval_days=1,"
        " stripe_price_id='price_1TP38n1kFVtkWldSLUJ1zRpi' WHERE name='business'"
    )
