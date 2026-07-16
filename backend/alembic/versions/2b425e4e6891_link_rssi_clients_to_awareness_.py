"""link rssi_clients to awareness_organizations

Revision ID: 2b425e4e6891
Revises: 929f830c094d
Create Date: 2026-07-16 07:05:37.479761

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b425e4e6891"
down_revision: str | None = "929f830c094d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Migration limitee a la colonne de liaison rssi_clients.awareness_organization_id
# (le drift d'autogenerate — JSONB->Text, NOT NULL — est volontairement ecarte).

_FK = "fk_rssi_clients_awareness_organization_id"


def upgrade() -> None:
    op.add_column(
        "rssi_clients", sa.Column("awareness_organization_id", sa.Integer(), nullable=True)
    )
    op.create_index(
        op.f("ix_rssi_clients_awareness_organization_id"),
        "rssi_clients",
        ["awareness_organization_id"],
        unique=True,
    )
    op.create_foreign_key(
        _FK,
        "rssi_clients",
        "awareness_organizations",
        ["awareness_organization_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(_FK, "rssi_clients", type_="foreignkey")
    op.drop_index(op.f("ix_rssi_clients_awareness_organization_id"), table_name="rssi_clients")
    op.drop_column("rssi_clients", "awareness_organization_id")
