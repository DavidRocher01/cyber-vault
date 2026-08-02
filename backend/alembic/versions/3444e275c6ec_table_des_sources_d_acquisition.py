"""Table des sources d'acquisition

Revision ID: 3444e275c6ec
Revises: 4b6fae2210d3
Create Date: 2026-08-02

Support de l'onglet Acquisition (`docs/ANALYTICS.md`) : d'où viennent les
conversions, et lesquelles produisent du revenu.

Une seule table, et surtout **aucune colonne identifiant un visiteur** — ni
cookie, ni empreinte, ni jeton de session. On enregistre une conversion qui a
eu lieu, pas une navigation. C'est ce qui dispense de bandeau de consentement,
et c'est une contrainte à tenir : ne pas ajouter ici de colonne qui permettrait
de reconnaître quelqu'un avant qu'il ait converti.

Les deux clés étrangères sont en `ON DELETE SET NULL` : effacer un compte
(RGPD art. 17) doit détacher la statistique, pas la supprimer — un agrégat
anonyme n'a plus de caractère personnel.

Table neuve, aucune donnée touchée, aucun verrou sur l'existant.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "3444e275c6ec"
down_revision: str | None = "4b6fae2210d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sources_acquisition",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("evenement", sa.String(length=32), nullable=False),
        sa.Column("utm_source", sa.String(length=64), nullable=True),
        sa.Column("utm_medium", sa.String(length=64), nullable=True),
        sa.Column("utm_campaign", sa.String(length=64), nullable=True),
        sa.Column("referent_domaine", sa.String(length=128), nullable=True),
        sa.Column("page_atterrissage", sa.String(length=128), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("public_scan_id", sa.Integer(), nullable=True),
        sa.Column("montant_mensuel_cents", sa.Integer(), nullable=True),
        sa.Column("cree_le", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["public_scan_id"], ["public_scans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_acquisition_id", "sources_acquisition", ["id"])
    op.create_index("ix_sources_acquisition_evenement", "sources_acquisition", ["evenement"])
    op.create_index("ix_sources_acquisition_cree_le", "sources_acquisition", ["cree_le"])
    op.create_index("ix_sources_acquisition_user_id", "sources_acquisition", ["user_id"])
    # Les trois lectures de l'onglet, toutes bornées dans le temps.
    op.create_index(
        "ix_sources_acq_date_evenement", "sources_acquisition", ["cree_le", "evenement"]
    )
    op.create_index("ix_sources_acq_source", "sources_acquisition", ["utm_source"])


def downgrade() -> None:
    op.drop_index("ix_sources_acq_source", table_name="sources_acquisition")
    op.drop_index("ix_sources_acq_date_evenement", table_name="sources_acquisition")
    op.drop_index("ix_sources_acquisition_user_id", table_name="sources_acquisition")
    op.drop_index("ix_sources_acquisition_cree_le", table_name="sources_acquisition")
    op.drop_index("ix_sources_acquisition_evenement", table_name="sources_acquisition")
    op.drop_index("ix_sources_acquisition_id", table_name="sources_acquisition")
    op.drop_table("sources_acquisition")
