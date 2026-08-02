"""Article de blog : remettre les tarifs sur la grille de juillet 2026

Revision ID: f7fb572e4e16
Revises: 940d8244be0e
Create Date: 2026-08-01

L'article « Audit cybersécurité PME : combien ça coûte vraiment en 2026 ? » est
publié, référencé dans le sitemap, et annonçait encore la grille de
`l6m7n8o9p0q1_fix_plan_prices` — Starter 9,90 €, Pro 39,90 €, Business 49,90 €.

Or la production facture 49 / 149 / 390 € depuis la refonte du 2026-07-26
(`5bd2b7bbc548`). L'article annonçait donc des abonnements jusqu'à HUIT FOIS
moins chers que le prix réel, sur une page publique dont le sujet même est le
prix.

Les caractéristiques étaient fausses aussi : « 1 site » pour 5, « 3 sites » pour
25, « 10 sites » pour un nombre illimité, et des fréquences de scan
hebdomadaires alors que tous les plans payants scannent quotidiennement.

Les chaînes recherchées ci-dessous ont été relevées sur le contenu RÉELLEMENT
servi en production, pas déduites du code : un remplacement qui ne correspond
pas exactement ne lève aucune erreur, il ne fait simplement rien.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "f7fb572e4e16"
down_revision: str | None = "940d8244be0e"
branch_labels = None
depends_on = None

SLUG = "audit-cybersecurite-pme-prix-2026"

# (ancien, nouveau) — l'ancien doit correspondre au caractère près.
REPLACEMENTS = [
    (
        "<li><strong>Starter (9,90 €/mois)</strong> — 1 site, scan mensuel "
        "automatisé + rapport PDF</li>",
        "<li><strong>Starter (49 €/mois)</strong> — 5 sites, scan quotidien "
        "+ export PDF de conformité</li>",
    ),
    (
        "<li><strong>Pro (39,90 €/mois)</strong> — 3 sites, scan hebdomadaire + alertes email</li>",
        "<li><strong>Pro (149 €/mois)</strong> — 25 sites, scan quotidien "
        "+ surveillance Dark Web</li>",
    ),
    (
        "<li><strong>Business (49,90 €/mois)</strong> — 10 sites, scan quotidien "
        "+ tous les modules</li>",
        "<li><strong>Business (390 €/mois)</strong> — sites illimités, scan quotidien "
        "+ tous les modules</li>",
    ),
    (
        "<td>Abonnement Business</td><td>49,90 € HT/mois</td>",
        "<td>Abonnement Business</td><td>390 € HT/mois</td>",
    ),
]

REVERSE_REPLACEMENTS = [(new, old) for old, new in reversed(REPLACEMENTS)]


def _apply(conn, pairs: list[tuple[str, str]]) -> None:
    for old, new in pairs:
        conn.execute(
            sa.text(
                "UPDATE blog_posts SET html_content = REPLACE(html_content, :old, :new) "
                "WHERE slug = :slug"
            ),
            {"old": old, "new": new, "slug": SLUG},
        )


def upgrade() -> None:
    _apply(op.get_bind(), REPLACEMENTS)


def downgrade() -> None:
    _apply(op.get_bind(), REVERSE_REPLACEMENTS)
