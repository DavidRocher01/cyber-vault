"""add_tracking_to_phishing

Revision ID: m8n9o0p1q2r3
Revises: l7m8n9o0p1q2
Create Date: 2026-05-20 12:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'm8n9o0p1q2r3'
down_revision: Union[str, None] = 'l7m8n9o0p1q2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tracking_id per target (UUID, unique) — used in tracking pixel / click / landing URLs
    op.add_column('phishing_targets',
        sa.Column('tracking_id', sa.String(length=36), nullable=True)
    )
    op.create_index(
        op.f('ix_phishing_targets_tracking_id'),
        'phishing_targets', ['tracking_id'], unique=True
    )

    # look-alike domain stored on campaign (separate from the verified target domain)
    op.add_column('phishing_campaigns',
        sa.Column('lookalike_domain', sa.String(length=255), nullable=True)
    )
    # sending status: draft | ready | sending | active | completed | cancelled
    # (status column already exists, just documents the new value)


def downgrade() -> None:
    op.drop_column('phishing_campaigns', 'lookalike_domain')
    op.drop_index(op.f('ix_phishing_targets_tracking_id'), table_name='phishing_targets')
    op.drop_column('phishing_targets', 'tracking_id')
