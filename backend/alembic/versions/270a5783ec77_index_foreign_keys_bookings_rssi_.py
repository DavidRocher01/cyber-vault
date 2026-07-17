"""index foreign keys bookings rssi_actions subscriptions

Revision ID: 270a5783ec77
Revises: d2305a2ebb80
Create Date: 2026-07-17 16:12:41.236580

Postgres n'indexe PAS automatiquement les colonnes de cle etrangere (seulement
la PK referencee). Ces 3 FK n'avaient aucun index couvrant -> JOIN lents et
surtout DELETE cascade lents (chaque suppression du parent scanne toute la table
enfant). Detecte via pg_constraint. Les colonnes portent desormais index=True
dans les modeles (booking, rssi_action, subscription) ; cette migration cree les
index correspondants. IF NOT EXISTS = idempotent.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "270a5783ec77"
down_revision: str | None = "d2305a2ebb80"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEXES = [
    ("ix_bookings_slot_id", "bookings", "slot_id"),
    ("ix_rssi_actions_source_visit_id", "rssi_actions", "source_visit_id"),
    ("ix_subscriptions_plan_id", "subscriptions", "plan_id"),
]


def upgrade() -> None:
    for name, table, col in _INDEXES:
        op.execute(f'CREATE INDEX IF NOT EXISTS "{name}" ON "{table}" ("{col}")')


def downgrade() -> None:
    for name, *_ in _INDEXES:
        op.execute(f'DROP INDEX IF EXISTS "{name}"')
