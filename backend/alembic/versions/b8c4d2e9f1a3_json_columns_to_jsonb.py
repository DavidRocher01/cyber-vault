"""json columns to jsonb

Revision ID: b8c4d2e9f1a3
Revises: 6f5b7d420f72
Create Date: 2026-06-05 10:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "b8c4d2e9f1a3"
down_revision: str | None = "6f5b7d420f72"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # blog_posts.tags — JSON array (full migration: model type updated)
    op.execute("""
        ALTER TABLE blog_posts
        ALTER COLUMN tags TYPE JSONB
        USING CASE WHEN tags IS NULL OR tags = '' THEN '[]'::JSONB
                   ELSE tags::JSONB END
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_blog_posts_tags ON blog_posts USING gin(tags)")

    # scans.results_json — DB-level JSONB validation, Python code unchanged
    op.execute("""
        ALTER TABLE scans
        ALTER COLUMN results_json TYPE JSONB
        USING CASE WHEN results_json IS NULL OR results_json = '' THEN NULL
                   ELSE results_json::JSONB END
    """)

    # darkweb_dossiers.top_sources_json
    op.execute("""
        ALTER TABLE darkweb_dossiers
        ALTER COLUMN top_sources_json TYPE JSONB
        USING CASE WHEN top_sources_json IS NULL OR top_sources_json = '' THEN NULL
                   ELSE top_sources_json::JSONB END
    """)

    # rssi_clients.extra_data
    op.execute("""
        ALTER TABLE rssi_clients
        ALTER COLUMN extra_data TYPE JSONB
        USING CASE WHEN extra_data IS NULL OR extra_data = '' THEN NULL
                   ELSE extra_data::JSONB END
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_blog_posts_tags")
    op.execute("ALTER TABLE blog_posts ALTER COLUMN tags TYPE TEXT USING tags::TEXT")
    op.execute("ALTER TABLE scans ALTER COLUMN results_json TYPE TEXT USING results_json::TEXT")
    op.execute(
        "ALTER TABLE darkweb_dossiers ALTER COLUMN top_sources_json TYPE TEXT USING top_sources_json::TEXT"
    )
    op.execute("ALTER TABLE rssi_clients ALTER COLUMN extra_data TYPE TEXT USING extra_data::TEXT")
