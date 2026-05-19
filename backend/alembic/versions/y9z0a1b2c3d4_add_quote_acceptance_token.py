"""add acceptance token and timestamps to quotes

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'y9z0a1b2c3d4'
down_revision = 'x8y9z0a1b2c3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('quotes', sa.Column('acceptance_token', sa.String(64), nullable=True))
    op.add_column('quotes', sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('quotes', sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index('ix_quotes_acceptance_token', 'quotes', ['acceptance_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_quotes_acceptance_token', table_name='quotes')
    op.drop_column('quotes', 'rejected_at')
    op.drop_column('quotes', 'accepted_at')
    op.drop_column('quotes', 'acceptance_token')
