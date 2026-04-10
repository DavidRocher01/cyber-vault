"""add code_scans table

Revision ID: e1f2a3b4c5d6
Revises: d2e3f4a5b6c7
Create Date: 2026-04-09 00:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'code_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('repo_url', sa.String(1024), nullable=False),
        sa.Column('repo_name', sa.String(256), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('critical_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('high_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('medium_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('low_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.String(512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_code_scans_id', 'code_scans', ['id'], unique=False)
    op.create_index('ix_code_scans_user_id', 'code_scans', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_code_scans_user_id', table_name='code_scans')
    op.drop_index('ix_code_scans_id', table_name='code_scans')
    op.drop_table('code_scans')
