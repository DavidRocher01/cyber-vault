"""add password_reset_tokens

Revision ID: a1b2c3d4e5f6
Revises: 946fc7f76cb9
Create Date: 2026-04-04 00:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '946fc7f76cb9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(512), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_password_reset_tokens_token', 'password_reset_tokens', ['token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_password_reset_tokens_token', table_name='password_reset_tokens')
    op.drop_table('password_reset_tokens')
