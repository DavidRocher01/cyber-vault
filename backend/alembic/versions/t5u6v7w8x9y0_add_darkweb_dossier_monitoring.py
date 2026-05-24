"""add darkweb dossier monitoring fields

Revision ID: t5u6v7w8x9y0
Revises: s4t5u6v7w8x9
Create Date: 2026-05-23
"""
from alembic import op
import sqlalchemy as sa

revision = 't5u6v7w8x9y0'
down_revision = 's4t5u6v7w8x9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('darkweb_dossiers', sa.Column('monitor_active', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('darkweb_dossiers', sa.Column('last_monitored_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('darkweb_dossiers', sa.Column('next_monitor_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('darkweb_dossiers', sa.Column('severity_score', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('darkweb_dossiers', 'severity_score')
    op.drop_column('darkweb_dossiers', 'next_monitor_at')
    op.drop_column('darkweb_dossiers', 'last_monitored_at')
    op.drop_column('darkweb_dossiers', 'monitor_active')
