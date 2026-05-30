"""Fix Audit Flash price 245€ → 290€ in blog articles

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-05-19
"""

import sqlalchemy as sa

from alembic import op

revision: str = "v6w7x8y9z0a1"
down_revision: str | None = "u5v6w7x8y9z0"
branch_labels = None
depends_on = None

REPLACEMENTS = [
    ("à partir de 245 € HT", "à partir de 290 € HT"),
    ("un audit Flash à 245 €", "un audit Flash à 290 €"),
    ("Flash</td><td>245 € HT</td>", "Flash</td><td>290 € HT</td>"),
    ("audit Flash (245 € HT", "audit Flash (290 € HT"),
]

REVERSE = [(new, old) for old, new in reversed(REPLACEMENTS)]


def _apply(conn, pairs):
    for old, new in pairs:
        conn.execute(
            sa.text("UPDATE blog_posts SET html_content = REPLACE(html_content, :old, :new)"),
            {"old": old, "new": new},
        )


def upgrade() -> None:
    _apply(op.get_bind(), REPLACEMENTS)


def downgrade() -> None:
    _apply(op.get_bind(), REVERSE)
