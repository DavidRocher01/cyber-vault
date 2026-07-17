"""add missing performance indexes

Revision ID: d2305a2ebb80
Revises: f23062c5b864
Create Date: 2026-07-17 16:06:25.810580

Contexte : ces 12 index sont declares dans les modeles ORM (Index(...) /
index=True) mais la migration qui les cree n'a JAMAIS ete generee -> ils sont
absents de la base (donc de la prod). Les requetes correspondantes ("lister mes
scans par statut", etc.) font un full-scan a l'echelle. On les cree ici, tant
que le volume est faible (pre-lancement) : CREATE INDEX est quasi instantane.

Cette migration est CUREE a la main : l'autogenerate voulait AUSSI supprimer des
index utiles presents en prod mais non declares dans les modeles (gin sur
blog_posts.tags, rssi_activity, contact_messages...) et renommer des contraintes
unique. Ces points sont volontairement EXCLUS ici (ils feront l'objet d'une
reconciliation modeles<->schema separee) pour ne rien casser en prod.

"""

from collections.abc import Sequence

from alembic import op

revision: str = "d2305a2ebb80"
down_revision: str | None = "f23062c5b864"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (index_name, table, [columns], unique)
_INDEXES = [
    ("ix_code_scans_status", "code_scans", ["status"], False),
    ("ix_code_scans_user_id_created_at", "code_scans", ["user_id", "created_at"], False),
    ("ix_code_scans_user_id_status", "code_scans", ["user_id", "status"], False),
    ("ix_public_scans_session_token", "public_scans", ["session_token"], True),
    ("ix_scans_site_id_finished_at", "scans", ["site_id", "finished_at"], False),
    ("ix_scans_site_id_status", "scans", ["site_id", "status"], False),
    ("ix_scans_status", "scans", ["status"], False),
    ("ix_subscriptions_status", "subscriptions", ["status"], False),
    ("ix_subscriptions_user_id_status", "subscriptions", ["user_id", "status"], False),
    ("ix_url_scans_status", "url_scans", ["status"], False),
    ("ix_url_scans_user_id_created_at", "url_scans", ["user_id", "created_at"], False),
    ("ix_url_scans_user_id_status", "url_scans", ["user_id", "status"], False),
]


def upgrade() -> None:
    # IF NOT EXISTS : idempotent, et sans risque si un index avait deja ete pose
    # a la main sur un environnement.
    for name, table, cols, unique in _INDEXES:
        uniq = "UNIQUE " if unique else ""
        col_list = ", ".join(f'"{c}"' for c in cols)
        op.execute(f'CREATE {uniq}INDEX IF NOT EXISTS "{name}" ON "{table}" ({col_list})')


def downgrade() -> None:
    for name, *_ in _INDEXES:
        op.execute(f'DROP INDEX IF EXISTS "{name}"')
