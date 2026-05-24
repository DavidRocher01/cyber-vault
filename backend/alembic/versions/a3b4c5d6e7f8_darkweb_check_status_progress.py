"""darkweb dossier check_status and progress tracking

Revision ID: a3b4c5d6e7f8
Revises: z0a1b2c3d4e5
Create Date: 2026-05-23

"""
from alembic import op
import sqlalchemy as sa

revision = 'a3b4c5d6e7f8'
down_revision = 't5u6v7w8x9y0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # verified_clean | exposed | api_error | rate_limited | pending
    op.add_column(
        'darkweb_dossier_targets',
        sa.Column('check_status', sa.String(20), nullable=True, server_default='pending'),
    )
    op.add_column(
        'darkweb_dossiers',
        sa.Column('checked_count', sa.Integer, nullable=True, server_default='0'),
    )
    op.add_column(
        'darkweb_dossiers',
        sa.Column('unverified_count', sa.Integer, nullable=True, server_default='0'),
    )


def downgrade() -> None:
    op.drop_column('darkweb_dossier_targets', 'check_status')
    op.drop_column('darkweb_dossiers', 'checked_count')
    op.drop_column('darkweb_dossiers', 'unverified_count')
