"""pricing grid update and allow_conformity_export

Revision ID: 5bd2b7bbc548
Revises: eb7e53b74bfe
Create Date: 2026-07-26 07:08:51.070883

Refonte tarifaire (project_pricing_review, tranchée 2026-07-25) :
  - Ajoute la colonne plans.allow_conformity_export (export NIS2/ISO réservé aux payants).
  - Réaligne les 4 plans sur la grille cible (Gratuit 0€ / Starter 49€ / Pro 149€ /
    Business 390€) avec quotas de sites et fréquence de scan différenciés.

Rétro-compatible (contrainte rollback code-only recette) : l'ajout de colonne a un
server_default, et l'UPDATE ne touche que des colonnes déjà connues de l'image précédente.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5bd2b7bbc548"
down_revision: str | None = "eb7e53b74bfe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_plans = sa.table(
    "plans",
    sa.column("name", sa.String),
    sa.column("price_eur", sa.Integer),
    sa.column("max_sites", sa.Integer),
    sa.column("scan_interval_days", sa.Integer),
    sa.column("tier_level", sa.Integer),
    sa.column("allow_conformity_export", sa.Boolean),
)

# name, price_eur (centimes), max_sites (-1=illimité), scan_interval_days, tier_level, export
_NEW_GRID = [
    ("free", 0, 1, 30, 1, False),
    ("starter", 4900, 5, 1, 2, True),
    ("pro", 14900, 25, 1, 3, True),
    ("business", 39000, -1, 1, 4, True),
]

# Ancienne grille (avant refonte) — pour le downgrade.
_OLD_GRID = [
    ("free", 0, -1, 1, 1),
    ("starter", 1490, -1, 1, 2),
    ("pro", 4900, -1, 1, 3),
    ("business", 14900, -1, 1, 4),
]


def upgrade() -> None:
    op.add_column(
        "plans",
        sa.Column(
            "allow_conformity_export",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    conn = op.get_bind()
    for name, price, max_sites, interval, tier, export in _NEW_GRID:
        conn.execute(
            _plans.update()
            .where(_plans.c.name == name)
            .values(
                price_eur=price,
                max_sites=max_sites,
                scan_interval_days=interval,
                tier_level=tier,
                allow_conformity_export=export,
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    for name, price, max_sites, interval, tier in _OLD_GRID:
        conn.execute(
            _plans.update()
            .where(_plans.c.name == name)
            .values(
                price_eur=price,
                max_sites=max_sites,
                scan_interval_days=interval,
                tier_level=tier,
            )
        )
    op.drop_column("plans", "allow_conformity_export")
