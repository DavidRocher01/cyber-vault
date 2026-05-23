"""add darkweb_scans table

Revision ID: i4j5k6l7m8n9
Revises: h3i4j5k6l7m8
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'i4j5k6l7m8n9'
down_revision = 'h3i4j5k6l7m8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'darkweb_scans',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('total_breaches', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(16), nullable=False, server_default='OK'),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('results_json', sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_table('darkweb_scans')
