"""sujet de l evaluation nis2 : client_id et unicite par sujet

Revision ID: 2a3bd12ceaea
Revises: e59d0ef982d0
Create Date: 2026-08-07 00:43:06.006025

L'evaluation NIS2 etait unique par compte. Elle devient unique par SUJET :
`client_id` a NULL designe l'auto-evaluation du titulaire, une valeur designe le
dossier monte pour ce client. Un consultant peut donc en detenir autant que de
clients suivis.

POURQUOI `NULLS NOT DISTINCT`. PostgreSQL considere par defaut deux NULL comme
distincts : sans cette clause, `UNIQUE (user_id, client_id)` laisserait un meme
compte creer une infinite d'auto-evaluations personnelles. Le code qui les lit
fait un `scalar_one_or_none()` et se mettrait a lever des la deuxieme. Clause
disponible depuis PostgreSQL 15 ; la plateforme est en 17.

CE FICHIER A ETE REPRIS APRES AUTOGENERATE. Deux defauts du `downgrade` genere :
la contrainte de cle etrangere y etait supprimee par le nom `None`, et l'unicite
par compte y etait recreee AVANT que les dossiers clients ne disparaissent — donc
en echec des qu'un consultant en detenait plus d'un.
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2a3bd12ceaea"
down_revision: str | None = "e59d0ef982d0"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

FK_CLIENT = "nis2_assessments_client_id_fkey"


def upgrade() -> None:
    op.add_column("nis2_assessments", sa.Column("client_id", sa.Integer(), nullable=True))

    # L'index sur user_id etait unique : c'est ce qui portait « une evaluation
    # par compte ». Il redevient un index de recherche ordinaire, l'unicite
    # passant a la contrainte de couple ci-dessous.
    op.drop_constraint("uq_nis2_assessments_user_id", "nis2_assessments", type_="unique")
    op.drop_index("ix_nis2_assessments_user_id", table_name="nis2_assessments")
    op.create_index(
        op.f("ix_nis2_assessments_user_id"), "nis2_assessments", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_nis2_assessments_client_id"), "nis2_assessments", ["client_id"], unique=False
    )

    op.create_unique_constraint(
        "uq_nis2_assessments_user_client",
        "nis2_assessments",
        ["user_id", "client_id"],
        postgresql_nulls_not_distinct=True,
    )

    # CASCADE et non SET NULL : si la fiche client disparait, son dossier n'a
    # plus d'objet. Le repasser a NULL le confondrait avec l'auto-evaluation
    # personnelle du consultant, en y versant les reponses d'un tiers.
    op.create_foreign_key(
        FK_CLIENT,
        "nis2_assessments",
        "rssi_clients",
        ["client_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # CE DELETE DETRUIT DES DONNEES, ET IL EST INEVITABLE. Le schema d'avant ne
    # tolere qu'une evaluation par compte : les dossiers montes pour des clients
    # n'y ont aucune place. Sans cet effacement prealable, la recreation de
    # `uq_nis2_assessments_user_id` echouerait des qu'un consultant en detient
    # plus d'un — et la migration ne serait pas reversible.
    op.execute("DELETE FROM nis2_assessments WHERE client_id IS NOT NULL")

    op.drop_constraint(FK_CLIENT, "nis2_assessments", type_="foreignkey")
    op.drop_constraint("uq_nis2_assessments_user_client", "nis2_assessments", type_="unique")
    op.drop_index(op.f("ix_nis2_assessments_client_id"), table_name="nis2_assessments")
    op.drop_index(op.f("ix_nis2_assessments_user_id"), table_name="nis2_assessments")

    op.create_index("ix_nis2_assessments_user_id", "nis2_assessments", ["user_id"], unique=True)
    op.create_unique_constraint("uq_nis2_assessments_user_id", "nis2_assessments", ["user_id"])
    op.drop_column("nis2_assessments", "client_id")
