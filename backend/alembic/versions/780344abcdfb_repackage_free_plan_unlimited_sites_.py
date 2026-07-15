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
    # Repackage des plans existants (le seed _seed_plans ne fait qu'un INSERT-if-absent, il ne
    # met PAS a jour les plans deja en base : cette data-migration s'en charge en prod).
    #   max_sites -> -1 sur TOUS les plans (sites illimites : chaque tier inclut le precedent,
    #     et le Gratuit est deja illimite ; cf. subscription_service.UNLIMITED_SITES).
    #   scan_interval_days -> 1 sur TOUS les plans (scan quotidien : idem, le Gratuit est deja
    #     quotidien, un plan payant ne peut pas scanner moins souvent).
    op.execute("UPDATE plans SET max_sites = -1, scan_interval_days = 1")


def downgrade() -> None:
    # Restaure les valeurs d'origine :
    #   max_sites : free 1, starter 1, pro 5, business 15
    #   scan_interval_days : free 0, starter 7, pro 7, business 1
    op.execute("UPDATE plans SET max_sites = 1 WHERE name IN ('free', 'starter')")
    op.execute("UPDATE plans SET max_sites = 5 WHERE name = 'pro'")
    op.execute("UPDATE plans SET max_sites = 15 WHERE name = 'business'")
    op.execute("UPDATE plans SET scan_interval_days = 0 WHERE name = 'free'")
    op.execute("UPDATE plans SET scan_interval_days = 7 WHERE name IN ('starter', 'pro')")
    op.execute("UPDATE plans SET scan_interval_days = 1 WHERE name = 'business'")
