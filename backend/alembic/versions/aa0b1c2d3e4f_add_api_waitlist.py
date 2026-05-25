"""add api_waitlist table

Revision ID: aa0b1c2d3e4f
Revises: z0a1b2c3d4e5, c2d3e4f5a6b7
Create Date: 2026-05-24

"""
from alembic import op
import sqlalchemy as sa

revision = 'aa0b1c2d3e4f'
down_revision = ('z0a1b2c3d4e5', 'c2d3e4f5a6b7')
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'api_waitlist',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('company', sa.String(150), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('api_waitlist')
