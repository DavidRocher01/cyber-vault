"""notifications.created_at en timestamptz

Le modele Notification declarait ``DateTime`` sans ``timezone=True`` alors que
son default fournit ``datetime.now(UTC)`` (tz-aware). asyncpg refusait donc
chaque insert :

    invalid input for query argument $7: ...
    (can't subtract offset-naive and offset-aware datetimes)

Consequence en prod : aucune notification in-app n'etait jamais creee, et la
session SQLAlchemy empoisonnee faisait echouer en cascade l'email d'alerte de
scan URL. Les deux echecs etaient avales en ``logger.warning``.

Retro-compatible : l'ancienne image ecrit deja des datetimes tz-aware (ils
passent desormais) et relit des valeurs aware sans probleme.

Revision ID: 940d8244be0e
Revises: d3b47ded55b3
Create Date: 2026-07-29 16:10:52.595074

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "940d8244be0e"
down_revision: str | None = "d3b47ded55b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Les valeurs naives deja presentes ont ete ecrites en UTC par le code
    # applicatif : on les reinterprete comme telles.
    op.execute(
        "ALTER TABLE notifications "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE notifications "
        "ALTER COLUMN created_at TYPE TIMESTAMP WITHOUT TIME ZONE "
        "USING created_at AT TIME ZONE 'UTC'"
    )
