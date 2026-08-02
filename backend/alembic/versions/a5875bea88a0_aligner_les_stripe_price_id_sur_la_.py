"""Aligner les stripe_price_id sur la grille de juillet 2026

Revision ID: a5875bea88a0
Revises: f7fb572e4e16
Create Date: 2026-08-02

Les identifiants de prix Stripe n'existaient nulle part dans le dépôt : ils
avaient été posés à la main en production via `scripts/set_stripe_price_ids.py`.
Les seules valeurs versionnées étaient celles de trois migrations d'avril
(`k5l6m7n8o9p0`, `m7n8o9p0q1r2`, `o9p0q1r2s3t4`), qui désignent des prix à
9,90 / 39,90 / 49,90 € — archivés chez Stripe le 2026-08-02.

Conséquence : une base reconstruite, ou restaurée depuis un point antérieur,
serait repartie en facturant 9,90 € un abonnement affiché 49 €. Sur la
production actuelle, cette migration ne change rien — les valeurs y sont déjà
correctes ; elle les rend reproductibles.

Les identifiants sont recopiés en dur, et non importés de `app.core.pricing` :
une migration doit rester un instantané fidèle de ce qui a été appliqué ce
jour-là. Aucune autre migration du dépôt n'importe de code applicatif, et une
grille qui bouge ne doit pas réécrire l'histoire rétroactivement.

C'est `test_pricing_source_unique.py` qui empêche les deux de diverger : il
échoue tant qu'un identifiant de la grille n'apparaît dans aucune migration —
ce qui force à en écrire une nouvelle, jamais à retoucher celle-ci.

Sûre à rejouer : `UPDATE ... WHERE name = :name` ne crée rien et ne touche que
les trois plans payants. Le `downgrade` ne restaure pas les anciens
identifiants — ils désignent des prix archivés, les remettre réarmerait le piège
qu'on ferme ici. Il vide les colonnes, ce qui bloque proprement le checkout
(400, « Plan not configured in Stripe yet ») au lieu de facturer à côté.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "a5875bea88a0"
down_revision: str | None = "f7fb572e4e16"
branch_labels = None
depends_on = None

# {plan: (price_id mensuel, price_id annuel)} — grille du 2026-07-26,
# 49 / 149 / 390 € par mois, l'annuel valant dix mois.
PRICE_IDS = {
    "starter": ("price_1TxQ6B1kFVtkWldS5UuJBANP", "price_1TxQ6Z1kFVtkWldS2NK9MR3v"),
    "pro": ("price_1TxQ811kFVtkWldS6j432oEy", "price_1TxQ8K1kFVtkWldSuwGN0x5K"),
    "business": ("price_1TxQ9Z1kFVtkWldS3zxEZK9H", "price_1TxQA91kFVtkWldS3cxc9zMa"),
}

_SQL = sa.text(
    "UPDATE plans SET stripe_price_id = :mensuel, stripe_price_id_yearly = :annuel "
    "WHERE name = :name"
)


def upgrade() -> None:
    conn = op.get_bind()
    for name, (mensuel, annuel) in PRICE_IDS.items():
        conn.execute(_SQL, {"name": name, "mensuel": mensuel, "annuel": annuel})


def downgrade() -> None:
    conn = op.get_bind()
    for name in PRICE_IDS:
        conn.execute(_SQL, {"name": name, "mensuel": "", "annuel": ""})
