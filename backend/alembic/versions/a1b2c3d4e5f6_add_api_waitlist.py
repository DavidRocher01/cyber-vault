"""add api_waitlist table

Revision ID: a1b2c3d4e5f6
Revises: z0a1b2c3d4e5
Create Date: 2026-05-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'a1b2c3d4e5f6'
down_revision = 'z0a1b2c3d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_waitlist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('company', sa.String(150), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_api_waitlist_email', 'api_waitlist', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_api_waitlist_email', table_name='api_waitlist')
    op.drop_table('api_waitlist')
