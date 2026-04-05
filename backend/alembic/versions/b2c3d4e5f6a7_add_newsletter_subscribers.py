"""add newsletter_subscribers

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-04-05 00:00:00.000000

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'newsletter_subscribers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('subscribed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('unsubscribe_token', sa.String(512), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_newsletter_subscribers_email', 'newsletter_subscribers', ['email'], unique=True)
    op.create_index('ix_newsletter_subscribers_unsubscribe_token', 'newsletter_subscribers', ['unsubscribe_token'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_newsletter_subscribers_unsubscribe_token', table_name='newsletter_subscribers')
    op.drop_index('ix_newsletter_subscribers_email', table_name='newsletter_subscribers')
    op.drop_table('newsletter_subscribers')
