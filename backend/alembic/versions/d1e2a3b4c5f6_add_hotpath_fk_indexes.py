"""add indexes on hot-path foreign keys

Revision ID: d1e2a3b4c5f6
Revises: b7f3e1a9c2d4
Create Date: 2026-07-03 15:30:00.000000

Ajoute des index sur des colonnes ForeignKey filtrées fréquemment mais qui n'en
avaient pas (PostgreSQL n'indexe pas automatiquement les FK) :

- vault_items.owner_id          : filtré à CHAQUE opération du coffre
                                  (WHERE owner_id = current_user.id — liste/détail/maj/suppr)
- refresh_tokens.user_id        : révocation en masse par utilisateur (logout, reset mdp)
- password_reset_tokens.user_id : invalidation des tokens non consommés par utilisateur

Sans index, ces filtres font un sequential scan qui se dégrade quand les tables
grandissent. Noms d'index alignés sur la convention SQLAlchemy (ix_<table>_<col>)
pour rester cohérent avec les modèles (index=True).
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d1e2a3b4c5f6"
down_revision: str | None = "b7f3e1a9c2d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_vault_items_owner_id", "vault_items", ["owner_id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_vault_items_owner_id", table_name="vault_items")
