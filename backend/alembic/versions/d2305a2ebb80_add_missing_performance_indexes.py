"""add missing performance indexes

Contexte : verification du schema reel (=prod) le 2026-07-17. Un seul index
declare dans les modeles ORM manquait reellement en base : l'index UNIQUE sur
public_scans.session_token. Les autres index de perf (scans/url_scans/
code_scans/subscriptions sur status et colonnes composites) existent deja en
prod depuis la migration a2b3c4d5e6f7 (2026-04-13) -- il ne faut donc PAS les
recreer ici, sinon deux migrations gerent le meme index et le downgrade tente
un double DROP (cf test_migration_cycle).

public_scans.session_token est declare unique dans le modele mais la migration
de creation de la table (i3j4k5l6m7n8) ne posait pas l'index : verifie sur RDS
prod qu'il n'y a ni doublon ni NULL avant de poser l'index unique.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d2305a2ebb80"
down_revision: str | None = "f23062c5b864"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # IF NOT EXISTS : idempotent (sans risque si l'index a deja ete pose a la main).
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS "ix_public_scans_session_token" '
        'ON "public_scans" ("session_token")'
    )


def downgrade() -> None:
    op.execute('DROP INDEX IF EXISTS "ix_public_scans_session_token"')
