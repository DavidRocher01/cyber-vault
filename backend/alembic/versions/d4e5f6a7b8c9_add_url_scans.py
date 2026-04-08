"""add url_scans table

Revision ID: d4e5f6a7b8c9
Revises: b2c3d4e5f6a7
Create Date: 2026-04-08 00:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'url_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('verdict', sa.String(20), nullable=True),
        sa.Column('threat_type', sa.String(50), nullable=True),
        sa.Column('threat_score', sa.Integer(), nullable=True),
        sa.Column('screenshot_path', sa.String(512), nullable=True),
        sa.Column('results_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_url_scans_id', 'url_scans', ['id'], unique=False)
    op.create_index('ix_url_scans_user_id', 'url_scans', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_url_scans_user_id', table_name='url_scans')
    op.drop_index('ix_url_scans_id', table_name='url_scans')
    op.drop_table('url_scans')
