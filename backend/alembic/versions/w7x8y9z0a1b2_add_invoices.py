"""Add invoices table

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-05-19
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "w7x8y9z0a1b2"
down_revision: Union[str, None] = "v6w7x8y9z0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_number", sa.String(20), nullable=False),
        sa.Column("invoice_seq", sa.Integer(), nullable=False),
        sa.Column("invoice_year", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("client_name", sa.String(255), nullable=False),
        sa.Column("client_email", sa.String(255), nullable=False),
        sa.Column("client_address", sa.Text(), nullable=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="paid"),
        sa.Column("stripe_invoice_id", sa.String(255), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"], unique=True)
    op.create_index("ix_invoices_user_id_issue_date", "invoices", ["user_id", "issue_date"])
    op.create_index("ix_invoices_year_seq", "invoices", ["invoice_year", "invoice_seq"])
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_invoices_user_id", "invoices")
    op.drop_index("ix_invoices_year_seq", "invoices")
    op.drop_index("ix_invoices_user_id_issue_date", "invoices")
    op.drop_index("ix_invoices_invoice_number", "invoices")
    op.drop_index("ix_invoices_id", "invoices")
    op.drop_table("invoices")
