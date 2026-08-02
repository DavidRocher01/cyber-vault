"""Ajouter le rôle admin sur les comptes

Revision ID: 4b6fae2210d3
Revises: a5875bea88a0
Create Date: 2026-08-02

L'administration de la plateforme reposait sur `ADMIN_API_KEY` : un secret
partagé statique, sans identité, sans révocation, sans 2FA — relevé par l'audit
du 2026-07-27. `users.is_admin` porte désormais ce droit sur un compte, donc sur
une identité traçable et révocable.

**Aucun compte n'est promu ici.** La colonne arrive à `false` pour tout le monde,
y compris les comptes existants. C'est délibéré : accorder l'administration par
migration reviendrait à décider en aveugle qui est administrateur, et une
migration rejouée sur une base restaurée reconduirait ce choix sans que personne
ne le revoie.

La promotion passe par `scripts/create_admin.py`, en accès direct au conteneur
(`aws ecs execute-command`) — donc par quelqu'un qui a déjà les droits AWS.

Additive et instantanée : ajout d'une colonne avec `server_default`, aucun
verrou long sur `users`.
"""

import sqlalchemy as sa

from alembic import op

revision: str = "4b6fae2210d3"
down_revision: str | None = "a5875bea88a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_admin")
