"""add darkweb dossier tables

Revision ID: s4t5u6v7w8x9
Revises: r3s4t5u6v7w8
Create Date: 2026-05-23
"""

import sqlalchemy as sa

from alembic import op

revision = "s4t5u6v7w8x9"
down_revision = "r3s4t5u6v7w8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── breach_catalog ────────────────────────────────────────────────────────
    op.create_table(
        "breach_catalog",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("breach_date", sa.String(20), nullable=True),
        sa.Column("added_date", sa.String(40), nullable=True),
        sa.Column("pwn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("data_classes_json", sa.Text(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_sensitive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_fabricated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_spam_list", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_breach_catalog_id", "breach_catalog", ["id"])
    op.create_index("ix_breach_catalog_name", "breach_catalog", ["name"], unique=True)

    # ── darkweb_dossiers ──────────────────────────────────────────────────────
    op.create_table(
        "darkweb_dossiers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("company_name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_emails", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("exposed_emails", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_breach_instances", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("top_sources_json", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_darkweb_dossiers_id", "darkweb_dossiers", ["id"])
    op.create_index("ix_darkweb_dossiers_user_id", "darkweb_dossiers", ["user_id"])

    # ── darkweb_dossier_targets ───────────────────────────────────────────────
    op.create_table(
        "darkweb_dossier_targets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "dossier_id",
            sa.Integer(),
            sa.ForeignKey("darkweb_dossiers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("total_breaches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("breach_sources_json", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_darkweb_dossier_targets_id", "darkweb_dossier_targets", ["id"])
    op.create_index(
        "ix_darkweb_dossier_targets_dossier_id",
        "darkweb_dossier_targets",
        ["dossier_id"],
    )
    op.create_index("ix_darkweb_dossier_targets_email", "darkweb_dossier_targets", ["email"])


def downgrade() -> None:
    op.drop_index("ix_darkweb_dossier_targets_email", "darkweb_dossier_targets")
    op.drop_index("ix_darkweb_dossier_targets_dossier_id", "darkweb_dossier_targets")
    op.drop_index("ix_darkweb_dossier_targets_id", "darkweb_dossier_targets")
    op.drop_table("darkweb_dossier_targets")

    op.drop_index("ix_darkweb_dossiers_user_id", "darkweb_dossiers")
    op.drop_index("ix_darkweb_dossiers_id", "darkweb_dossiers")
    op.drop_table("darkweb_dossiers")

    op.drop_index("ix_breach_catalog_name", "breach_catalog")
    op.drop_index("ix_breach_catalog_id", "breach_catalog")
    op.drop_table("breach_catalog")
