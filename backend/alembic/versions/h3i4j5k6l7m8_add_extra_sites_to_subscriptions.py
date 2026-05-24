"""add extra_sites to subscriptions

Revision ID: h3i4j5k6l7m8
Revises: g2h3i4j5k6l7
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'h3i4j5k6l7m8'
down_revision = 'g2h3i4j5k6l7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('subscriptions', sa.Column('extra_sites', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('subscriptions', 'extra_sites')
