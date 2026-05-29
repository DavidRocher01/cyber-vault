"""add composite index on awareness_learners org active

Revision ID: 977a962a96fb
Revises: 087da233d9f0
Create Date: 2026-05-29 19:27:09.356780

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "977a962a96fb"
down_revision: str | None = "087da233d9f0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_awareness_learners_org_active",
        "awareness_learners",
        ["organization_id", "is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_awareness_learners_org_active", table_name="awareness_learners")
