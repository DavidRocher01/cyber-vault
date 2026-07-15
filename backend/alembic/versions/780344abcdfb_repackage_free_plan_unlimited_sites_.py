"""repackage free plan unlimited sites daily scans

Revision ID: 780344abcdfb
Revises: d1e2a3b4c5f6
Create Date: 2026-07-15 14:42:09.992072

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "780344abcdfb"
down_revision: str | None = "d1e2a3b4c5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Repackage du plan Gratuit existant (le seed _seed_plans ne fait qu'un INSERT-if-absent,
    # il ne met PAS a jour les plans deja en base : cette data-migration s'en charge en prod).
    #   max_sites: 1 -> -1  (sites illimites, cf. subscription_service.UNLIMITED_SITES)
    #   scan_interval_days: 0 -> 1  (scan automatique quotidien)
    op.execute("UPDATE plans SET max_sites = -1, scan_interval_days = 1 WHERE name = 'free'")


def downgrade() -> None:
    op.execute("UPDATE plans SET max_sites = 1, scan_interval_days = 0 WHERE name = 'free'")
