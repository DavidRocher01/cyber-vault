"""add client_user_id to rssi_clients (portail client)

Revision ID: 929f830c094d
Revises: 780344abcdfb
Create Date: 2026-07-15 22:10:14.084041

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "929f830c094d"
down_revision: str | None = "780344abcdfb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# NB : migration volontairement limitee a la colonne rssi_clients.client_user_id.
# L'autogenerate captait aussi du drift pre-existant (conventions d'index, JSONB->Text...)
# sans rapport avec cette feature : ecarte pour ne pas toucher a la prod.

_FK = "fk_rssi_clients_client_user_id_users"


def upgrade() -> None:
    op.add_column("rssi_clients", sa.Column("client_user_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_rssi_clients_client_user_id"),
        "rssi_clients",
        ["client_user_id"],
        unique=True,
    )
    op.create_foreign_key(_FK, "rssi_clients", "users", ["client_user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint(_FK, "rssi_clients", type_="foreignkey")
    op.drop_index(op.f("ix_rssi_clients_client_user_id"), table_name="rssi_clients")
    op.drop_column("rssi_clients", "client_user_id")
