"""Fix blog post pricing — replace old plan names with Starter/Pro/Business

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-05-17
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "u5v6w7x8y9z0"
down_revision: Union[str, None] = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None

SLUG = "audit-cybersecurite-pme-prix-2026"

# Old → new replacements (order matters: do list items before table row)
REPLACEMENTS = [
    (
        "<li><strong>Vigie (~99 €/mois)</strong> — scan hebdomadaire automatisé + alerte immédiate en cas de nouveau risque</li>",
        "<li><strong>Starter (9,90 €/mois)</strong> — 1 site, scan mensuel automatisé + rapport PDF</li>",
    ),
    (
        "<li><strong>Sentinelle (~199 €/mois)</strong> — scan quotidien + rapport mensuel + ligne directe en cas d'incident</li>",
        "<li><strong>Pro (39,90 €/mois)</strong> — 3 sites, scan hebdomadaire + alertes email</li>",
    ),
    (
        "<li><strong>Blindage 360 (~499 €/mois)</strong> — surveillance continue + audit trimestriel + revue de code mensuelle</li>",
        "<li><strong>Business (49,90 €/mois)</strong> — 10 sites, scan quotidien + tous les modules</li>",
    ),
    (
        "<td>Abonnement Sentinelle</td><td>199 € HT/mois</td>",
        "<td>Abonnement Business</td><td>49,90 € HT/mois</td>",
    ),
]

REVERSE_REPLACEMENTS = [(new, old) for old, new in reversed(REPLACEMENTS)]


def _apply(conn, pairs: list[tuple[str, str]]) -> None:
    for old, new in pairs:
        conn.execute(
            sa.text(
                "UPDATE blog_posts SET html_content = REPLACE(html_content, :old, :new) WHERE slug = :slug"
            ),
            {"old": old, "new": new, "slug": SLUG},
        )


def upgrade() -> None:
    conn = op.get_bind()
    _apply(conn, REPLACEMENTS)


def downgrade() -> None:
    conn = op.get_bind()
    _apply(conn, REVERSE_REPLACEMENTS)
