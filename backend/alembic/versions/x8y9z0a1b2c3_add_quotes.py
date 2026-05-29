"""add quotes table

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-05-19
"""

import sqlalchemy as sa

from alembic import op

revision = "x8y9z0a1b2c3"
down_revision = "w7x8y9z0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("quote_number", sa.String(20), nullable=False),
        sa.Column("quote_seq", sa.Integer(), nullable=False),
        sa.Column("quote_year", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_email", sa.String(255), nullable=False),
        sa.Column("client_address", sa.Text(), nullable=True),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="30"),
        # sent | accepted | rejected | expired
        sa.Column("status", sa.String(20), nullable=False, server_default="sent"),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_quotes_id", "quotes", ["id"], unique=False)
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"], unique=True)
    op.create_index("ix_quotes_year_seq", "quotes", ["quote_year", "quote_seq"], unique=False)
    op.create_index("ix_quotes_user_id", "quotes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_quotes_user_id", table_name="quotes")
    op.drop_index("ix_quotes_year_seq", table_name="quotes")
    op.drop_index("ix_quotes_quote_number", table_name="quotes")
    op.drop_index("ix_quotes_id", table_name="quotes")
    op.drop_table("quotes")
