"""fichiers deposes : SET NULL au lieu de CASCADE

La premiere version du registre cascadait sur users et rssi_clients. L intention
etait RGPD : le compte parti, ses depots n ont plus de titulaire. L effet obtenu
etait l inverse.

Une cascade efface la LIGNE. Elle ne touche pas a l objet sur S3, que seul du
code applicatif sait supprimer. Supprimer un client laissait donc le fichier
stocke ET effacait la seule trace permettant de le retrouver — exactement ce que
ce registre existe pour empecher, reintroduit par l autre bout. Les deux
suppressions sont atteignables depuis l application : DELETE /rssi/clients/{id}
et DELETE /users/me.

Avec SET NULL, la ligne survit, perd son rattachement, et devient un orphelin au
sens de `purger_orphelins` : objet efface PUIS ligne, avec reessai si le stockage
resiste. Le fichier disparait reellement sous DELAI_ORPHELIN_JOURS.

`depose_par_id` devient nullable : perdre le deposant n empeche pas de purger, et
le conserver apres suppression du compte serait precisement la donnee sans base
legale qu on voulait eviter.

Les noms de contraintes sont ecrits EXPLICITEMENT des deux cotes. L autogenerate
avait produit `op.drop_constraint(None, ...)` dans le downgrade, qui aurait
echoue le jour ou on en aurait eu besoin.

Revision ID: 294593b3e4cc
Revises: 56974e23d737
Create Date: 2026-08-05 11:17:43.952904

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "294593b3e4cc"
down_revision: str | None = "56974e23d737"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_CLIENT = "fichiers_deposes_client_id_fkey"
FK_DEPOSANT = "fichiers_deposes_depose_par_id_fkey"


def upgrade() -> None:
    op.alter_column("fichiers_deposes", "depose_par_id", existing_type=sa.INTEGER(), nullable=True)
    op.drop_constraint(FK_CLIENT, "fichiers_deposes", type_="foreignkey")
    op.drop_constraint(FK_DEPOSANT, "fichiers_deposes", type_="foreignkey")
    op.create_foreign_key(
        FK_CLIENT, "fichiers_deposes", "rssi_clients", ["client_id"], ["id"], ondelete="SET NULL"
    )
    op.create_foreign_key(
        FK_DEPOSANT, "fichiers_deposes", "users", ["depose_par_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    # Revenir en arriere suppose qu'aucune ligne ne porte `depose_par_id` nul,
    # sinon la remise en NOT NULL echoue. C'est le prix du retour a un schema
    # qui, lui, perdait des fichiers.
    op.drop_constraint(FK_DEPOSANT, "fichiers_deposes", type_="foreignkey")
    op.drop_constraint(FK_CLIENT, "fichiers_deposes", type_="foreignkey")
    op.create_foreign_key(
        FK_DEPOSANT, "fichiers_deposes", "users", ["depose_par_id"], ["id"], ondelete="CASCADE"
    )
    op.create_foreign_key(
        FK_CLIENT, "fichiers_deposes", "rssi_clients", ["client_id"], ["id"], ondelete="CASCADE"
    )
    op.alter_column("fichiers_deposes", "depose_par_id", existing_type=sa.INTEGER(), nullable=False)
