"""revert scans darkweb rssi json columns to text

Revision ID: f23062c5b864
Revises: 2b425e4e6891
Create Date: 2026-07-16 14:27:28.354828

Contexte : la migration b8c4d2e9f1a3 avait converti 4 colonnes JSON en JSONB
pour une validation cote base. Mais les modeles ORM (scans.results_json,
darkweb_dossiers.top_sources_json, rssi_clients.extra_data) sont restes en
Text et le code les manipule comme des chaines JSON (json.dumps / json.loads).
Avec SQLAlchemy 2.0 + asyncpg (render_bind_cast), chaque parametre Text est
caste en ::VARCHAR, ce que PostgreSQL refuse d'inserer dans une colonne JSONB
(DatatypeMismatchError) -> tout INSERT sur ces 3 tables echoue.

Cette migration repasse ces 3 colonnes en TEXT pour aligner base <-> modeles
<-> code. blog_posts.tags reste en JSONB (modele correctement type en JSONB).
La conversion jsonb -> text via ::text preserve le contenu (json.loads reste OK).

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f23062c5b864"
down_revision: str | None = "2b425e4e6891"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE scans ALTER COLUMN results_json TYPE TEXT USING results_json::TEXT")
    op.execute(
        "ALTER TABLE darkweb_dossiers "
        "ALTER COLUMN top_sources_json TYPE TEXT USING top_sources_json::TEXT"
    )
    op.execute("ALTER TABLE rssi_clients ALTER COLUMN extra_data TYPE TEXT USING extra_data::TEXT")


def downgrade() -> None:
    op.execute("""
        ALTER TABLE scans
        ALTER COLUMN results_json TYPE JSONB
        USING CASE WHEN results_json IS NULL OR results_json = '' THEN NULL
                   ELSE results_json::JSONB END
    """)
    op.execute("""
        ALTER TABLE darkweb_dossiers
        ALTER COLUMN top_sources_json TYPE JSONB
        USING CASE WHEN top_sources_json IS NULL OR top_sources_json = '' THEN NULL
                   ELSE top_sources_json::JSONB END
    """)
    op.execute("""
        ALTER TABLE rssi_clients
        ALTER COLUMN extra_data TYPE JSONB
        USING CASE WHEN extra_data IS NULL OR extra_data = '' THEN NULL
                   ELSE extra_data::JSONB END
    """)
