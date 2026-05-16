"""Add booking_slots and bookings tables

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-05-16
"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "s3t4u5v6w7x8"
down_revision: Union[str, None] = "r2s3t4u5v6w7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "booking_slots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.String(10), nullable=False),
        sa.Column("time", sa.String(5), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("label", sa.String(200), nullable=False, server_default="Appel découverte"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_booking_slots_date", "booking_slots", ["date"])

    op.create_table(
        "bookings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), sa.ForeignKey("booking_slots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("need_type", sa.String(50), nullable=False),
        sa.Column("message", sa.String(2000), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="confirmed"),
        sa.Column("cancel_token", sa.String(128), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookings_cancel_token", "bookings", ["cancel_token"])


def downgrade() -> None:
    op.drop_index("ix_bookings_cancel_token", table_name="bookings")
    op.drop_table("bookings")
    op.drop_index("ix_booking_slots_date", table_name="booking_slots")
    op.drop_table("booking_slots")
